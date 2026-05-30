# Workshop Lead-to-CRM Autopilot — Makefile
# Usage: make <target>

.PHONY: help dev test build deploy ssl renew logs restart stop ps shell

APP_DOMAIN := vestint.duckdns.org
N8N_DOMAIN := vestint-n8n.duckdns.org

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Local Development ──────────────────────────────────────────────────────────

dev: ## Start local dev server (in-memory DB, no SSL)
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run all tests
	.venv/Scripts/python -m pytest tests/ -v --tb=short

test-docker: ## Run tests inside Docker
	docker compose --profile test run --rm test

# ── Production ────────────────────────────────────────────────────────────────

build: ## Build Docker image
	docker compose build --no-cache

ssl: ## Issue SSL certs (first time only). Requires EMAIL env var.
	@[ -n "$(EMAIL)" ] || (echo "ERROR: make ssl EMAIL=you@email.com" && exit 1)
	EMAIL=$(EMAIL) bash scripts/init-ssl.sh

ssl-staging: ## Test SSL issuance without rate limits (staging certs)
	@[ -n "$(EMAIL)" ] || (echo "ERROR: make ssl-staging EMAIL=you@email.com" && exit 1)
	EMAIL=$(EMAIL) STAGING=1 bash scripts/init-ssl.sh

renew: ## Renew SSL certs (run automatically via cron)
	bash scripts/renew-ssl.sh

deploy: ## Full production deploy (build + up)
	docker compose --profile production build
	docker compose --profile production up -d
	@echo ""
	@echo "✅ Deployed!"
	@echo "   App: https://$(APP_DOMAIN)"
	@echo "   n8n: https://$(N8N_DOMAIN)"

# ── Operations ────────────────────────────────────────────────────────────────

up: ## Start all services
	docker compose --profile production up -d

down: ## Stop all services
	docker compose --profile production down

restart: ## Restart app service only
	docker compose restart app

stop: ## Stop all services and remove containers
	docker compose --profile production down --remove-orphans

ps: ## Show service status
	docker compose ps

logs: ## Tail all logs
	docker compose logs -f --tail=50

logs-app: ## Tail app logs only
	docker compose logs -f --tail=100 app

logs-nginx: ## Tail nginx access/error logs
	docker compose logs -f --tail=50 nginx

logs-n8n: ## Tail n8n logs
	docker compose logs -f --tail=50 n8n

shell: ## Open shell in app container
	docker compose exec app /bin/bash

nginx-reload: ## Reload nginx config (after cert renewal)
	docker compose exec nginx nginx -s reload

nginx-test: ## Test nginx config syntax
	docker compose exec nginx nginx -t

# ── Cron setup ────────────────────────────────────────────────────────────────

cron-setup: ## Install auto-renewal cron (runs twice daily)
	@echo "Installing SSL renewal cron..."
	(crontab -l 2>/dev/null; echo "0 0,12 * * * cd $(shell pwd) && make renew >> /var/log/certbot-renew.log 2>&1") | crontab -
	@echo "✓ Cron installed: daily at 00:00 and 12:00"
	crontab -l
