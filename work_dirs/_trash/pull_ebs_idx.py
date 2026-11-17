# -*- coding: utf-8 -*-
"""拉搜索页索引 manifest+分片，统计型号库 SEO 数据源规模。"""
import json
import re
import sys
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

TID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client


def get_asset(key):
    a = rest.request("GET", f"themes/{TID}/assets.json", params={"asset[key]": key})["asset"]
    return a.get("value") or ""


man = get_asset("assets/spec-idx-manifest.json")
print("manifest:", man[:300])
m = json.loads(man)
print("manifest keys:", list(m.keys()))
shards = m.get("shards") or m.get("pages") or []
print("shards:", len(shards), shards[:5])

items = []
for s in shards[:3] + shards[-1:]:  # 抽样 4 片
    v = get_asset(f"assets/{s}" if not s.startswith("assets/") else s)
    if not v:
        try:
            v = urllib.request.urlopen(f"https://www.estrybattery.com/cdn/shop/t/{TID}/assets/{s}").read().decode()
        except Exception as e:
            print("fetch fail", s, e)
            continue
    d = json.loads(v)
    arr = d.get("items") or d.get("data") or []
    items.extend(arr)
    print(s, "->", len(arr), "items, sample:", json.dumps(arr[0], ensure_ascii=False)[:220] if arr else "-")

with_handle = sum(1 for i in items if i.get("h"))
with_pn = sum(1 for i in items if i.get("pn"))
print(f"sample total={len(items)} withHandle={with_handle} withPn={with_pn}")
with open("/tmp/ebs_sample_items.json", "w") as f:
    json.dump(items[:50], f, ensure_ascii=False)
print("saved /tmp/ebs_sample_items.json")
