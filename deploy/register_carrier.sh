#!/bin/bash
set -e
cd /home/jason/shopify-admin
KEY=$(grep -E "^API_KEYS?=" .env | head -1 | cut -d= -f2 | cut -d, -f1 | tr -d ' "')
[ -n "$KEY" ] || { echo "FATAL: no API_KEYS in .env"; exit 1; }
H="X-API-Key: $KEY"

echo "== 1. stores in DB =="
STORES=$(curl -s -H "$H" "http://127.0.0.1:8100/stores")
echo "$STORES" | sed -E "s/shpat_[A-Za-z0-9]+/shpat_***/g" | head -c 800
echo

STORE_ID=$(echo "$STORES" | python3 -c "import sys,json; d=json.load(sys.stdin); lst=d if isinstance(d,list) else d.get('items',d.get('data',[])); s=[x for x in lst if x.get('is_available',True)]; print(s[0]['id'] if s else '')" 2>/dev/null)
[ -n "$STORE_ID" ] || { echo "FATAL: no available store"; exit 1; }
echo "== 2. registering carrier for store_id=$STORE_ID =="
curl -s -X POST -H "$H" "http://127.0.0.1:8100/shipping/carrier/register?store_id=$STORE_ID&callback_base_url=https://shopify-api.bornmieo.com" | head -c 500
echo

echo "== 3. verify registration =="
curl -s -H "$H" "http://127.0.0.1:8100/shipping/carrier/list?store_id=$STORE_ID" | head -c 400
echo
echo "== 4. simulate shopify checkout callback (public URL) =="
curl -s -m 10 -X POST -H "Content-Type: application/json" \
  -d '{"rate":{"items":[{"sku":"TEST","grams":500,"quantity":1}],"destination":{"country":"US","postal_code":"10001","city":"New York","province":"NY"}}}' \
  https://shopify-api.bornmieo.com/shopify/callback/carrier-rates | head -c 400
echo
echo DONE
