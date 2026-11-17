#!/bin/bash
cd /home/jason/shopify-admin
KEY=$(grep -E "^API_KEYS?=" .env | head -1 | cut -d= -f2 | cut -d, -f1 | tr -d ' "')
H="X-API-Key: $KEY"

echo "== 1. retry carrier registration (idempotent) =="
REG=$(curl -s -X POST -H "$H" "http://127.0.0.1:8100/shipping/carrier/register?store_id=1&callback_base_url=https://shopify-api.bornmieo.com")
echo "$REG" | head -c 500
echo

if echo "$REG" | grep -q "carrier_service"; then
  echo "REGISTRATION-SUCCEEDED"
  exit 0
fi

echo "== 2. CCS still off -> query store plan via GraphQL =="
grep -E "^DB_" .env | sed "s/PASSWORD=.*/PASSWORD=***/"
DBPASS=$(grep -E "^DB_PASSWORD=" .env | head -1 | cut -d= -f2 | tr -d ' "')
DBUSER=$(grep -E "^DB_USER" .env | head -1 | cut -d= -f2 | tr -d ' "')
DBNAME=$(grep -E "^DB_NAME" .env | head -1 | cut -d= -f2 | tr -d ' "')
DBHOST=$(grep -E "^DB_HOST" .env | head -1 | cut -d= -f2 | tr -d ' "'); DBHOST=${DBHOST:-127.0.0.1}
echo "user=$DBNAME host=$DBHOST db=$DBNAME"
TOKEN=$(mysql -h$DBHOST -N -u$DBUSER -p"$DBPASS" $DBNAME -e "select api_key from stores where id=1" 2>/dev/null)
SHOP=$(mysql -h$DBHOST -N -u$DBUSER -p"$DBPASS" $DBNAME -e "select domain from stores where id=1" 2>/dev/null)
[ -n "$TOKEN" ] || { echo "FATAL: cannot read store token"; exit 1; }
curl -s -m 15 -X POST -H "X-Shopify-Access-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"{ shop { name plan { displayName partnerDevelopment shopifyPlus } primaryDomain { host } } }"}' \
  "https://${SHOP}.myshopify.com/admin/api/2025-01/graphql.json"
echo
