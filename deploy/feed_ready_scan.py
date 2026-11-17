# -*- coding: utf-8 -*-
"""全店产品 Google Shopping feed 就绪度扫描(只读)。"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

params = {"limit": 250, "status": "active",
          "fields": "id,handle,vendor,product_type,variants"}
allp = []
while True:
    time.sleep(1.2)
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    allp += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>")
           for x in link.split(",") if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

n = len(allp)
vars_ = [v for p in allp for v in p.get("variants") or []]
vendor = sum(1 for p in allp if (p.get("vendor") or "").strip())
ptype = sum(1 for p in allp if (p.get("product_type") or "").strip())
gtin = sum(1 for v in vars_ if (v.get("barcode") or "").strip())
sku = sum(1 for v in vars_ if (v.get("sku") or "").strip())
price0 = sum(1 for v in vars_
             if not (v.get("price") or "0").strip("0.") and v.get("price") != "0.00")
grams = sum(1 for v in vars_ if v.get("grams"))
noreprice = sum(1 for v in vars_ if v.get("compare_at_price"))
print(f"active 品 {n}, 变体 {len(vars_)}")
print(f"vendor(brand) 填充: {vendor}/{n} = {vendor*100//max(n,1)}%")
print(f"product_type 填充: {ptype}/{n} = {ptype*100//max(n,1)}%")
print(f"barcode(GTIN) 填充: {gtin}/{len(vars_)} = {gtin*100//max(len(vars_),1)}%")
print(f"sku 填充: {sku}/{len(vars_)} = {sku*100//max(len(vars_),1)}%")
print(f"克重填充: {grams}/{len(vars_)} = {grams*100//max(len(vars_),1)}%")
print(f"划线价(compare_at) 设置: {noreprice}/{len(vars_)}")
vc = {}
for p in allp:
    k = (p.get("vendor") or "(空)").strip() or "(空)"
    vc[k] = vc.get(k, 0) + 1
print("vendor 分布 top8:", sorted(vc.items(), key=lambda x: -x[1])[:8])
