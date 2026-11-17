"""品牌切换 Estry 前探测：店铺设置/产品 vendor/主题资产/前台渲染的 Bomibattery 痕迹。"""
import json
import re
import subprocess
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

THEME_ID = 136764817652
rest = ShopifyRest(StoreService().get_client(1))
c = rest.client

# 1) 店铺名与域名
shop = c.request("GET", "shop.json", params={
    "fields": "name,domain,primary_domain,myshopify_domain"})["shop"]
print("shop:", json.dumps(shop, ensure_ascii=False))

# 2) 22 产品 vendor / title / handle 痕迹
pid, vendors, hit_t, hit_h, n = None, {}, 0, 0, 0
while True:
    params = {"limit": 50, "fields": "id,vendor,title,handle"}
    if pid:
        params["since_id"] = pid
    items = c.request("GET", "products.json", params=params).get("products", [])
    if not items:
        break
    for p in items:
        n += 1
        vendors[p["vendor"]] = vendors.get(p["vendor"], 0) + 1
        hit_t += "bomibattery" in p["title"].lower()
        hit_h += "bomibattery" in p["handle"].lower()
    pid = items[-1]["id"]
    if len(items) < 50:
        break
print(f"products: {n} | vendors: {vendors} | title hit: {hit_t} | handle hit: {hit_h}")

# 3) 主题资产扫描（text 类逐个 GET，含品牌字样计数）
assets = c.request("GET", f"themes/{THEME_ID}/assets.json").get("assets", [])
keys = [a["key"] for a in assets if a.get("content_type") != "image"]
print("text assets:", len(keys), "/", len(assets))
PAT = re.compile(r"bomibattery", re.I)
hits = []
for k in keys:
    try:
        v = c.request("GET", f"themes/{THEME_ID}/assets.json",
                      params={"asset[key]": k})["asset"]
        s = v.get("value") or ""
        if PAT.search(s):
            hits.append((k, len(PAT.findall(s))))
    except Exception as e:
        print("ERR", k, str(e)[:70])
print("asset hits:", hits)

# 4) 前台实际渲染（主页 + 集合页）
for url in ("https://www.bornmieo.com/", "https://www.bornmieo.com/collections/all"):
    html = subprocess.run(["curl", "-skL", url], capture_output=True,
                          text=True, timeout=60).stdout
    ms = [m.group(0).replace("\n", " ") for m in
          re.finditer(r".{30}[Bb]omibattery.{30}", html)]
    print(f"front {url.split('/')[-2] or 'home'}: {len(ms)} hits")
    for s in ms[:5]:
        print("   ", s)
