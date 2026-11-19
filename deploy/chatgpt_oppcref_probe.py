"""补查：Shopify 全量订单里 oppcref（OpenAI 点击追踪参数）形态的 ChatGPT 目录单"""
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores import StoreService

BJ = timezone(timedelta(hours=8))
client = StoreService().get_client(1)
all_orders, since_id = [], 0
while True:
    page = client.request("GET", "orders.json", params={
        "status": "any", "limit": 250, "since_id": since_id,
        "fields": "id,name,created_at,total_price,financial_status,cancelled_at,landing_site,referring_site",
    }).get("orders", [])
    all_orders.extend(page)
    if len(page) < 250:
        break
    since_id = page[-1]["id"]

hits = [o for o in all_orders
        if "oppcref" in (o.get("landing_site") or "").lower()
        or "oppcref" in (o.get("referring_site") or "").lower()]
print(f"全量 {len(all_orders)} 单中 oppcref 形态 {len(hits)} 单:")
for o in sorted(hits, key=lambda x: x["created_at"]):
    ts = datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")).astimezone(BJ)
    ls = o.get("landing_site") or ""
    has_utm = "utm_source" in ls.lower()
    flag = "已取消" if o.get("cancelled_at") else o.get("financial_status")
    print(f"  {o['name']}  {ts:%Y-%m-%d}  ${o['total_price']}  {flag}"
          f"  utm={'有' if has_utm else '无(纯oppcref)'}")
    print(f"    landing_site={ls[:130]}")
