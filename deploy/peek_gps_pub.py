# -*- coding: utf-8 -*-
"""查 gps-navigator-battery collection 发布状态 + 全 38 落地页发布核对。"""
import json
import time

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
from shopify_admin.services.stores.service import StoreService  # noqa

client = StoreService().get_client(1)
plans = json.load(open("/tmp/allcat_plans.json"))
need = {p["url"].rsplit("/", 1)[-1] for p in plans}

found = {}
for ep, key in (("smart_collections.json", "smart_collections"),
                ("custom_collections.json", "custom_collections")):
    since = 0
    while True:
        batch = client.request("GET", ep, params={
            "limit": 250, "since_id": since}).get(key, [])
        if not batch:
            break
        for c in batch:
            if c["handle"] in need:
                found[c["handle"]] = c
        since = batch[-1]["id"]
        time.sleep(0.35)

unpub = []
for h in sorted(need):
    c = found.get(h)
    if not c:
        print("MISSING:", h)
    elif not c.get("published_at"):
        unpub.append(h)
        print("UNPUBLISHED:", h, c["id"], c["title"])
print(f"\n未发布 {len(unpub)} / {len(need)}:", unpub)
g = found.get("gps-navigator-battery")
if g:
    print("GPS collection:", json.dumps(
        {k: g.get(k) for k in ("id", "handle", "title", "published_at",
                               "products_count", "sort_order")},
        ensure_ascii=False))
client.close()
