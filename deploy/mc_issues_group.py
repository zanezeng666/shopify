# -*- coding: utf-8 -*-
"""按 code 分组看违规样例与影响渠道，产出修复分组决策表。只读。"""
import json
from collections import defaultdict

recs = json.load(open("/home/jason/shopify-admin/deploy/mc_issues_20261116.json"))
by_code = defaultdict(list)
for r in recs:
    for i in r["issues"]:
        by_code[i["code"]].append((r, i))

print(f"{'code':40s} {'产品数':>4} {'免费位dis':>8} {'广告位dis':>8}")
for code, lst in sorted(by_code.items(), key=lambda x: -len(x[1])):
    fr = sum(1 for r, _ in lst
             if r["ctx"].get("FREE_LISTINGS") == "disapproved")
    ad = sum(1 for r, _ in lst
             if r["ctx"].get("SHOPPING_ADS") == "disapproved")
    print(f"{code:40s} {len(lst):4d} {fr:8d} {ad:8d}")

for code in ("guns_parts_policy_violation", "landing_page_error",
             "endangered_species_policy_violation", "tobacco_policy_violation",
             "personal_hardships_policy_violation",
             "item_missing_required_attribute"):
    lst = by_code.get(code, [])
    if not lst:
        continue
    print(f"\n== {code} 样例 ==")
    for r, i in lst[:5]:
        print(f"  offer={r['offerId'][:24]} free={r['ctx'].get('FREE_LISTINGS','-'):10s}"
              f" ads={r['ctx'].get('SHOPPING_ADS','-'):10s} img={r['image']}")
        print(f"    title: {r['title'][:66]}")
        print(f"    link : {r['link'][:80]}")
        print(f"    desc : {i['desc'][:80]} | {i['detail'][:80]}")
