"""范围补探测：9719 存量品的 status 分布 + body_html 品牌字样比例（全量扫）。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
c = rest.client
PAT = re.compile(r"bomibattery", re.I)

pid = None
stat = {}          # status -> [count, body_hit, vendor_bomi]
n = 0
while True:
    params = {"limit": 250, "fields": "id,vendor,status,body_html"}
    if pid:
        params["since_id"] = pid
    items = c.request("GET", "products.json", params=params).get("products", [])
    if not items:
        break
    for p in items:
        n += 1
        s = stat.setdefault(p["status"], [0, 0, 0])
        s[0] += 1
        s[1] += bool(PAT.search(p.get("body_html") or ""))
        s[2] += p["vendor"].lower() == "bomibattery"
    pid = items[-1]["id"]
    if n % 2500 == 0:
        print(f"...scanned {n}", flush=True)
    if len(items) < 250:
        break

print("total:", n)
for s, (cnt, body_hit, vendor) in sorted(stat.items()):
    print(f"  {s}: {cnt} | body含品牌: {body_hit} | vendor=Bomibattery: {vendor}")
