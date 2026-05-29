# n8n vs Python Backend — Анализ распределения логики

## Текущая архитектура (AS-IS)

Сейчас система работает по принципу **n8n как тупой планировщик, Python как умный исполнитель**:

```
n8n (каждые 15 мин) ──HTTP──► POST /api/v1/webhooks/n8n/sla-check
                                        │
                               Python check_sla() — вся логика здесь

n8n (каждый час)    ──HTTP──► POST /api/v1/webhooks/n8n/followup-trigger
                                        │
                               Python process_followups() — вся логика здесь
```

n8n сейчас делает ровно одно: **тригеррит HTTP-запросы по расписанию**. Всё остальное — Python.

---

## Что потенциально можно перенести в n8n

### Категория 1 — Scheduling / Triggers (✅ прямой кандидат)

Уже частично перенесено, но можно усилить:

| Что сейчас | В Python | Можно в n8n |
|---|---|---|
| SLA check schedule | APScheduler в `main.py` | n8n Schedule Trigger → HTTP call |
| Follow-up schedule | APScheduler в `main.py` | n8n Schedule Trigger → HTTP call |
| IMAP polling | APScheduler + `imap_intake.py` | n8n IMAP Email Trigger (нативный нод) |

**Вывод по scheduling:** n8n выигрывает. У него есть встроенный UI для расписаний, история запусков, retry-логика, и визуальный debugger. APScheduler внутри FastAPI — это скрытая зависимость, которая падает вместе с приложением.

---

### Категория 2 — Routing / Conditional Logic (⚠️ спорно)

Пример: текущая логика `pipeline.py` — если `score_label == "cold"`, пропустить CRM.

```python
# Python сейчас
if score_label == "cold":
    await _log(..., "crm_upsert_skipped", ...)
    return
elif crm.is_configured():
    result = await crm.full_upsert(lead_data)
```

Это же можно собрать в n8n как **IF → HTTP Node** цепочку. Но:

- В n8n нет доступа к внутренним Python-объектам (Pydantic models, ORM)
- Каждый шаг — отдельный HTTP-запрос → latency накапливается
- Транзакционность теряется: если n8n нода упала на шаге 3 из 5, частичный результат уже записан

**Вывод:** Логику ветвления внутри pipeline НЕ стоит переносить в n8n. Это не то, для чего он создан.

---

### Категория 3 — Notifications / Outbound (✅ хороший кандидат)

Сейчас Telegram-уведомления отправляются из Python через `httpx`. n8n имеет нативный **Telegram нод** без кода.

| Что сейчас | В Python | Альтернатива в n8n |
|---|---|---|
| `send_new_lead_alert()` | httpx → Telegram API | n8n Telegram Node |
| `send_sla_alert()` | httpx → Telegram API | n8n Telegram Node |
| `send_alert()` (followup) | httpx → Telegram API | n8n Telegram Node |
| Будущий Slack/Email/WhatsApp | Новый код + зависимости | n8n готовые ноды |

**Главный аргумент:** если клиент захочет добавить Slack или email-дайджест, в Python это новый сервис + зависимость. В n8n — новый нод за 5 минут без деплоя.

---

### Категория 4 — Data Intake от внешних форм (✅ отличный кандидат)

Сейчас `/api/v1/webhooks/intake` вручную нормализует поля от Tally, Typeform, Webflow. В n8n это делается через визуальный field-mapping без единой строки кода:

```
Tally Webhook → n8n нод "Set" (маппинг полей) → POST /api/v1/leads
Typeform      → n8n нод "Set" (маппинг полей) → POST /api/v1/leads
Facebook Leads→ n8n Facebook Lead нод         → POST /api/v1/leads
```

Каждый новый источник лидов — новый n8n workflow, без изменения Python-кода.

---

### Категория 5 — LLM вызовы / Scoring (❌ не переносить)

n8n имеет LangChain-интеграцию и AI ноды. Технически можно вызывать LLM из n8n. Но:

- **Нет типизации** — Python Pydantic валидирует ответы LLM, парсит JSON, обрабатывает ошибки структурированно
- **Нет rule-based fallback** — `_rule_based_score()` сложно воспроизвести в n8n Code нодах
- **Нет тестируемости** — весь `tests/` покрывает эту логику через pytest/mock
- **Vendor lock** — если убрать LLM-логику из Python, тесты становятся бесполезными

**Вывод:** LLM-оркестрация — сердце системы. Она должна оставаться в Python.

---

### Категория 6 — CRM Adapter (❌ не переносить)

Паттерн адаптера (`HubSpotAdapter`, `PipedriveAdapter`) — это одна из главных архитектурных ценностей системы. Переносить в n8n означает:
- Потерять CRM-agnostic переключение через `.env`
- Написать CRM-логику заново в виде HTTP-ланчей n8n
- Потерять покрытие тестами (7 тестов в `test_crm_adapter.py`)

---

## Сводная таблица рекомендаций

| Компонент | Сейчас | Рекомендация | Причина |
|---|---|---|---|
| SLA schedule | APScheduler | **Перенести в n8n** | UI, история, retry |
| Follow-up schedule | APScheduler | **Перенести в n8n** | UI, история, retry |
| IMAP polling | APScheduler + Python | **Частично в n8n** | Нативный IMAP нод |
| Telegram alerts | Python httpx | **Перенести в n8n** | Нативный нод, масштабируемость каналов |
| Intake field mapping | Python `/webhooks/intake` | **Перенести в n8n** | No-code маппинг для каждого источника |
| Pipeline routing (if/else) | Python pipeline.py | **Оставить в Python** | Транзакционность, типизация |
| LLM scoring & intent | Python enricher.py | **Оставить в Python** | Тестируемость, fallback-логика |
| CRM upsert | Python crm/ | **Оставить в Python** | Adapter pattern, тесты |
| Draft generation | Python draft.py | **Оставить в Python** | Сложный parsing, fallback |
| Human approval flow | Python followup.py | **Оставить в Python** | Транзакционность, CRM sync |

---

## Целевая архитектура (TO-BE)

```
                    ┌─────────────────────────────────────┐
                    │              n8n                     │
                    │  ┌─────────────────────────────┐    │
  Tally Form ───────┤  │ Intake Workflow              │    │
  Typeform ─────────┤  │ Field mapping → POST /leads  │    │
  Facebook Leads ───┤  └─────────────────────────────┘    │
                    │                                      │
                    │  ┌─────────────────────────────┐    │
                    │  │ SLA Monitor (every 15 min)  │    │
                    │  │ → POST /webhooks/n8n/sla    │    │
                    │  │ → Telegram Node (breach)    │    │
                    │  └─────────────────────────────┘    │
                    │                                      │
                    │  ┌─────────────────────────────┐    │
                    │  │ Follow-up Scheduler (1h)    │    │
                    │  │ → POST /webhooks/followup   │    │
                    │  │ → Telegram Node (reminder)  │    │
                    │  └─────────────────────────────┘    │
                    └─────────────────────────────────────┘
                                     │ HTTP API
                    ┌────────────────▼────────────────────┐
                    │         Python FastAPI               │
                    │   normalize → dedup → LLM score      │
                    │   → CRM upsert → draft generation    │
                    │   → DB persistence → event log       │
                    └─────────────────────────────────────┘
```

---

## Главный вывод

**Граница должна проходить по принципу: n8n управляет "когда и откуда", Python управляет "как и что".**

- n8n = оркестратор событий и каналов (scheduling, intake normalization, notification delivery)
- Python = интеллектуальный ядро (LLM, scoring, CRM adapter, data integrity)

Перенос *всей* логики в n8n — антипаттерн. n8n Code ноды не тестируются pytest'ом, не имеют typed models, не дают git-diff при изменениях, и не масштабируются под нагрузкой (каждый нод — отдельный HTTP round-trip).

**Оптимальная стратегия — гибридная:** Python как надёжное API-ядро, n8n как no-code клей для источников данных, расписаний и каналов уведомлений.

---

## Связанные файлы

- `app/main.py` — текущий APScheduler (кандидат на замену n8n-триггерами)
- `app/services/imap_intake.py` — IMAP polling (частично заменяется n8n IMAP нодом)
- `app/services/alerts.py` — Telegram httpx (заменяется n8n Telegram нодом)
- `app/api/v1/webhooks.py` — эндпоинты для n8n-вызовов (остаются, расширяются)
- `n8n/workflows/` — существующие SLA и follow-up workflows
