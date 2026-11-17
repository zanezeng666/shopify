"""Which gateway did the 2 Nov orders actually use? Check transactions."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores import StoreService

client = StoreService().get_client(1)

orders = client.request("GET", "orders.json", params={"status": "any", "limit": 3})
for o in orders.get("orders", []):
    print(f"== {o.get('name')} {o.get('created_at')} ${o.get('total_price')} {o.get('financial_status')}")
    print(f"   gateway={o.get('gateway')}  processing_method={o.get('processing_method')}  source_name={o.get('source_name')}")
    txs = client.request("GET", f"orders/{o['id']}/transactions.json")
    for t in txs.get("transactions", []):
        print(f"   tx kind={t.get('kind')} gateway={t.get('gateway')} status={t.get('status')} amount=${t.get('amount')} message={str(t.get('message'))[:80]}")
