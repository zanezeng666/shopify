# -*- coding: utf-8 -*-
"""经 Shopify products.json 抓 medical-battery 产品图（前 10 张主图）。"""
import json
import urllib.request

url = ("https://www.estrybattery.com/collections/medical-battery"
       "/products.json?limit=50")
data = json.loads(urllib.request.urlopen(url, timeout=30).read())
prods = data.get("products", [])
print(f"产品数: {len(prods)}")
n = 0
for p in prods:
    imgs = p.get("images", [])
    if not imgs:
        continue
    src = imgs[0].get("src", "")
    if not src:
        continue
    dst = f"e:/worksapce/shopify/deploy/assets/prod_{n}.jpg"
    urllib.request.urlretrieve(src, dst)
    print("ok", n, p.get("title", "")[:40])
    n += 1
    if n >= 10:
        break
print(f"共下载 {n} 张")
