#!/bin/bash
cd /home/jason/shopify-admin
get(){ grep -E "^$1=" .env | head -1 | cut -d= -f2 | tr -d ' "'; }
DBPASS=$(get SHOPIFY_DB_PASSWORD); DBUSER=$(get SHOPIFY_DB_USER)
DBNAME=$(get SHOPIFY_DB_NAME); DBHOST=$(get SHOPIFY_DB_HOST); DBPORT=$(get SHOPIFY_DB_PORT); DBPORT=${DBPORT:-3306}
TOKEN=$(mysql -h$DBHOST -P$DBPORT -N -u$DBUSER -p"$DBPASS" $DBNAME -e "select api_key from stores where id=1" 2>/dev/null)
SHOP=$(mysql -h$DBHOST -P$DBPORT -N -u$DBUSER -p"$DBPASS" $DBNAME -e "select domain from stores where id=1" 2>/dev/null)
[ -n "$TOKEN" ] || { echo "FATAL: no token"; exit 1; }
echo "shop: $SHOP.myshopify.com"
curl -s -m 15 -X POST -H "X-Shopify-Access-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"{ shop { name plan { displayName partnerDevelopment shopifyPlus } } }"}' \
  "https://${SHOP}.myshopify.com/admin/api/2025-01/graphql.json"
echo
