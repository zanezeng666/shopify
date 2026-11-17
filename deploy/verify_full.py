# -*- coding: utf-8 -*-
"""全量合并终验：总数/巨组主品/301/soldout 残留。"""
import json
import sys
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,handle,title,variants", "status": "active"}
allp = []
while True:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    allp += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>")
           for x in link.split(",") if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
print(f"active 自建品总数: {len(allp)}")

mv = [p for p in allp if len(p.get("variants") or []) > 1]
print(f"多变体品: {len(mv)} | "
      f"变体总数 {sum(len(p['variants']) for p in mv)}")

# soldout 扫描: 线上 .js 按品查太慢，用库存 API 扫主品变体
soldout = 0
for p in mv[:400]:
    iids = [str(v["inventory_item_id"]) for v in p["variants"]
            if v.get("inventory_item_id")]
    r = cl._client.get("inventory_levels.json",
                       params={"inventory_item_ids": ",".join(iids[:50])},
                       auth=cl._auth)
    av = {}
    for x in r.json().get("inventory_levels", []):
        av[x["inventory_item_id"]] = x["available"]
    for v in p["variants"]:
        if av.get(v.get("inventory_item_id")) == 0:
            soldout += 1
print(f"抽 400 品 soldout(0库存)变体: {soldout}")

# 巨组主品抽查
for pref in ("battery-for-proscenic-lds-m7-pro-m6",
             "battery-for-blaupunkt-bluebot-xsmart",
             "battery-for-worx-landroid-s300"):
    p = next((x for x in allp if x["handle"].startswith(pref)), None)
    if not p:
        print(f"!! 未找到 {pref}")
        continue
    seq = [v["option1"] for v in
           sorted(p["variants"], key=lambda x: x["position"])]
    skus = all(v.get("sku") for v in p["variants"])
    print(f"\n{p['title'][:130]}")
    print(f"  变体序 {seq} sku齐={skus} 标题长={len(p['title'])}")

# 301 抽查 3 个被删页（38页组 Arnagar 成员/24页组 Kitfort 成员/普通组）
TESTS = ["battery-for-arnagar-s8-s8-pro-2",
         "battery-for-kitfort-kr-2505"]
for h in TESTS:
    req = urllib.request.Request(f"https://estrybattery.com/products/{h}",
                                 method="HEAD")
    class NR(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        urllib.request.build_opener(NR).open(req, timeout=20)
        print(f"301 {h}: 无跳转(未删?)")
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location", "")
        print(f"301 {h} -> {loc[:70]} ({e.code})")
