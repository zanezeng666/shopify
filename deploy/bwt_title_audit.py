# -*- coding: utf-8 -*-
"""BWT 问题审计①：全量产品标题长度分布 + 下架产品死链清单（供 IndexNow 通知）。只读。"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

cl = ShopifyRest(StoreService().get_client(1)).client

allp = []
params = {"limit": 250, "fields": "id,handle,title,status"}
while True:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    allp += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>")
           for x in link.split(",") if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1],
              "fields": "id,handle,title,status"}
    time.sleep(0.5)

print(f"产品总数 {len(allp)}")
active = [p for p in allp if p["status"] == "active"]
dead = [p for p in allp if p["status"] != "active"]
print(f"active {len(active)} / 非active(死链候选) {len(dead)}")

for th in (60, 70, 80, 100, 120):
    n = sum(1 for p in active if len(p["title"]) > th)
    print(f"  title > {th} 字符: {n}")

print("\n超长样例（>70，前 8）:")
for p in sorted(active, key=lambda x: -len(x["title"]))[:8]:
    print(f"  [{len(p['title'])}] {p['title'][:95]}")

print("\n死链样例（非 active，前 5）:")
for p in dead[:5]:
    print(f"  {p['status']} /products/{p['handle']}")

with open("/home/jason/shopify-admin/deploy/bwt_audit_result.json", "w") as f:
    json.dump(allp, f)
print("\n明细已存 deploy/bwt_audit_result.json")
