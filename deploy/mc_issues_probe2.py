# -*- coding: utf-8 -*-
"""补看 local_requirements/missing_attr/tobacco 样例 + landing_page_error 产品 Shopify 状态。只读。"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

recs = json.load(open("/home/jason/shopify-admin/deploy/mc_issues_20261116.json"))

# 去重：offerId+code
seen = set()
uniq = defaultdict(list)   # code -> [rec]
for r in recs:
    for i in r["issues"]:
        k = (r["offerId"], i["code"])
        if k in seen:
            continue
        seen.add(k)
        uniq[i["code"]].append((r, i))

print(f"{'code':40s} 去重产品数")
for c, lst in sorted(uniq.items(), key=lambda x: -len(x[1])):
    print(f"{c:40s} {len(lst):4d}")

for code in ("local_requirements_policy_violation",
             "item_missing_required_attribute", "tobacco_policy_violation",
             "local_stores_lack_inventory"):
    lst = uniq.get(code, [])
    if not lst:
        continue
    print(f"\n== {code} 样例 ==")
    for r, i in lst[:4]:
        print(f"  {r['offerId']} free={r['ctx'].get('FREE_LISTINGS','-')}")
        print(f"    {r['title'][:66]}")
        print(f"    desc: {i['desc'][:80]}")
        print(f"    detail: {i['detail'][:100]}")

# landing_page_error: 查 Shopify 产品状态
print("\n== landing_page_error 15 个产品 Shopify 状态 ==")
cl = ShopifyRest(StoreService().get_client(1)).client
for r, _ in uniq.get("landing_page_error", [])[:15]:
    pid = r["offerId"].replace("shopify_US_", "")
    try:
        p = cl.request("GET", f"products/{pid}.json",
                       params={"fields": "id,status,handle"})
        info = f"status={p['product']['status']} handle={p['product']['handle'][:50]}"
    except Exception as e:  # noqa
        info = f"GET 失败({type(e).__name__})→ 可能已删除"
    print(f"  {pid}: {info}")
    print(f"    MC link: {r['link'][:85]}")
