# -*- coding: utf-8 -*-
"""全量拉 3 分片统计：类目分布/handle 覆盖/可售类目候选。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

TID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client


def get_asset(key):
    a = rest.request("GET", f"themes/{TID}/assets.json", params={"asset[key]": key})["asset"]
    return a.get("value") or ""


items = []
for i in range(3):
    arr = json.loads(get_asset(f"assets/spec-idx-{i}.json"))
    print(f"shard {i}: {len(arr)}")
    items.extend(arr)
print("total items:", len(items))

# 字段全景
keys = {}
for it in items:
    for k in it:
        keys[k] = keys.get(k, 0) + 1
print("field coverage:", keys)

# 类目分布（若有）
cats = {}
for it in items:
    cat = it.get("cat") or it.get("c") or "?"
    cats[cat] = cats.get(cat, 0) + 1
print("categories:", sorted(cats.items(), key=lambda x: -x[1]))

with_h = [it for it in items if it.get("h")]
print(f"with product handle: {len(with_h)} / {len(items)}")

# DRAFT 三类（上架黑名单口径）
DRAFT_CATS = {"Mobile, SmartPhone", "Notebook, Laptop", "Camera"}
sellable = [it for it in items if (it.get("cat") or it.get("c")) not in DRAFT_CATS]
sellable_h = [it for it in sellable if it.get("h")]
print(f"sellable: {len(sellable)}, with handle: {len(sellable_h)}")

with open("/tmp/ebs_all_items.json", "w") as f:
    json.dump(items, f, ensure_ascii=False)
print("saved /tmp/ebs_all_items.json")
print("sample sellable+h:", json.dumps(sellable_h[:2], ensure_ascii=False)[:400])
