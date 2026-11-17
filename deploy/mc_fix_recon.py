# -*- coding: utf-8 -*-
"""死链3个状态 + 缺图8个图源调查 + 烟草1个定性。只读。"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, "/home/jason/shopify-admin")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import get_engine  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

recs = json.load(open("/home/jason/shopify-admin/deploy/mc_issues_20261116.json"))
seen, uniq = set(), defaultdict(list)
for r in recs:
    for i in r["issues"]:
        k = (r["offerId"], i["code"])
        if k not in seen:
            seen.add(k)
            uniq[i["code"]].append((r, i))

cl = ShopifyRest(StoreService().get_client(1)).client
eng = get_engine()

def pid_of(r):
    # offerId: shopify_US_<productID> 或 shopify_US_<productID>_<variantID>
    parts = r["offerId"].split("_")
    return parts[2], (parts[3] if len(parts) > 3 else "")

def show(r, tag):
    pid, vid = pid_of(r)
    try:
        p = cl.request("GET", f"products/{pid}.json",
                       params={"fields": "id,status,handle,title,images"})
        pd = p["product"]
        print(f"  [{tag}] {pid} status={pd['status']} imgs={len(pd['images'])}")
        print(f"      {pd['title'][:70]} /products/{pd['handle'][:55]}")
    except Exception as e:  # noqa
        print(f"  [{tag}] {pid} GET失败 {type(e).__name__} → 已删除?")

print("== landing_page_error 3 个 ==")
for r, _ in uniq["landing_page_error"]:
    show(r, "死链")
    print(f"      MC link: {r['link'][:85]}")

print("\n== item_missing_required_attribute 缺图 8 个 ==")
for r, _ in uniq["item_missing_required_attribute"]:
    show(r, "缺图")

print("\n== tobacco 1 个 ==")
for r, _ in uniq["tobacco_policy_violation"]:
    show(r, "烟草")

print("\n== 缺图产品库内图源线索（CS 远端 url/images 字段） ==")
with eng.connect() as c:
    for r, _ in uniq["item_missing_required_attribute"][:8]:
        pid, _ = pid_of(r)
        row = c.execute(text(
            "SELECT remote_url FROM products WHERE id=:i"), {"i": int(pid)}).first()
        print(f"  {pid} remote_url={row[0][:90] if row and row[0] else '无'}")
