#!/bin/bash
set -e
cd /home/jason/shopify-admin
echo "== pytest =="
.venv/bin/python -m pytest tests/test_sync_shopify.py -q 2>&1 | tail -3
echo "== 样例产品 id =="
.venv/bin/python - <<'PYEOF'
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest
rest = ShopifyRest(StoreService().get_client(1))
p = rest.product_by_handle("battery-for-delonghi-colombina-evo-xml510-as00000910")
print("PID:", p["id"])
PYEOF
