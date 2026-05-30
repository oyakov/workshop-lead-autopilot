#!/usr/bin/env bash
# =============================================================================
# renew-ssl.sh — Renew Let's Encrypt certs (run via cron every 12h)
# Certbot only actually renews when cert is within 30 days of expiry.
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[$(date)] Starting cert renewal check..."
docker compose run --rm certbot renew --quiet
docker compose exec nginx nginx -s reload
echo "[$(date)] Done."
