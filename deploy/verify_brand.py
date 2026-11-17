"""品牌切换验证：draft body 的 Estry 字样 + 全库 vendor 改名进度抽查。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client

# 1) 22 个 draft：body 应含 "Why Choose Estry" 且零 bomibattery
pid, n, estr, hit = None, 0, 0, 0
while True:
    params = {"limit": 50, "fields": "id,body_html,vendor", "status": "draft"}
    if pid:
        params["since_id"] = pid
    items = c.request("GET", "products.json", params=params).get("products", [])
    if not items:
        break
    for p in items:
        n += 1
        b = p.get("body_html") or ""
        estr += "Why Choose Estry" in b
        hit += bool(re.search(r"bomibattery", b, re.I))
        if p["vendor"] == "Estry":
            pass
    pid = items[-1]["id"]
    if len(items) < 50:
        break
print(f"draft: {n} | Why-Choose-Estry: {estr} | bomibattery-in-body: {hit}")

# 2) 跑批进度：全库 vendor 分布快照（前 2000 抽样）
pid, cnt = None, {"Estry": 0, "bomi": 0, "other": 0}
for _ in range(8):
    params = {"limit": 250, "fields": "id,vendor"}
    if pid:
        params["since_id"] = pid
    items = c.request("GET", "products.json", params=params).get("products", [])
    if not items:
        break
    for p in items:
        v = (p["vendor"] or "").lower()
        cnt["Estry" if v == "estry" else "bomi" if v == "bomibattery" else "other"] += 1
    pid = items[-1]["id"]
print(f"first-2000 vendor: {cnt}")
