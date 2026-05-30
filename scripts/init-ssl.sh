#!/usr/bin/env bash
# =============================================================================
# init-ssl.sh — First-time Let's Encrypt SSL setup for DuckDNS domains
#
# Usage (run once on the server, inside the project directory):
#   chmod +x scripts/init-ssl.sh
#   EMAIL=you@email.com ./scripts/init-ssl.sh
#
# What it does:
#   1. Creates temporary self-signed certs so nginx can start
#   2. Starts nginx
#   3. Runs certbot (HTTP-01 challenge via webroot)
#   4. Reloads nginx with real certs
# =============================================================================
set -euo pipefail

APP_DOMAIN="vestint.duckdns.org"
N8N_DOMAIN="vestint-n8n.duckdns.org"
EMAIL="${EMAIL:-}"
STAGING="${STAGING:-0}"   # set STAGING=1 to test without rate-limit

if [[ -z "$EMAIL" ]]; then
  echo "ERROR: Set EMAIL env var before running this script."
  echo "  EMAIL=you@email.com ./scripts/init-ssl.sh"
  exit 1
fi

CERTBOT_STAGING=""
if [[ "$STAGING" == "1" ]]; then
  CERTBOT_STAGING="--staging"
  echo "⚠️  Running in STAGING mode (test certs, not trusted)"
fi

echo "=== Step 1: Create temporary self-signed certs ==="
for domain in "$APP_DOMAIN" "$N8N_DOMAIN"; do
  cert_path="./certbot/conf/live/$domain"
  if [[ ! -f "$cert_path/fullchain.pem" ]]; then
    mkdir -p "$cert_path"
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
      -keyout "$cert_path/privkey.pem" \
      -out "$cert_path/fullchain.pem" \
      -subj "/CN=$domain" 2>/dev/null
    # nginx also needs chain.pem
    cp "$cert_path/fullchain.pem" "$cert_path/chain.pem"
    echo "  ✓ Temp cert created for $domain"
  else
    echo "  ✓ Cert already exists for $domain — skipping temp cert"
  fi
done

echo ""
echo "=== Step 2: Start nginx with temp certs ==="
docker compose up -d nginx
sleep 3
echo "  ✓ nginx started"

echo ""
echo "=== Step 3: Issue real certs via Let's Encrypt ==="
for domain in "$APP_DOMAIN" "$N8N_DOMAIN"; do
  echo "  Issuing cert for $domain ..."
  docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    $CERTBOT_STAGING \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$domain"
  echo "  ✓ Real cert issued for $domain"
done

echo ""
echo "=== Step 4: Reload nginx with real certs ==="
docker compose exec nginx nginx -s reload
echo "  ✓ nginx reloaded"

echo ""
echo "=== Step 5: Start remaining services ==="
docker compose up -d
echo "  ✓ All services started"

echo ""
echo "✅ SSL setup complete!"
echo "   App:  https://$APP_DOMAIN"
echo "   n8n:  https://$N8N_DOMAIN"
echo ""
echo "To enable auto-renewal (run once as cron):"
echo "  echo '0 12 * * * cd $(pwd) && ./scripts/renew-ssl.sh >> /var/log/certbot-renew.log 2>&1' | crontab -"
