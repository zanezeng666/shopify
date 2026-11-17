# -*- coding: utf-8 -*-
"""检查 dry-run 差集样本：offerId 形态 vs 类型字段。"""
import json

d = json.load(open("/home/jason/shopify-admin/deploy/mc_purge_state.json"))
print(f"dead={len(d['dead'])} live_skus={d['live_skus']} total_mc={d['total_mc']}")
for p in d["dead"][:8]:
    print(f"  id={p['id'][:66]}")
    print(f"    offer={p['offer'][:56]!r} types={str(p['types'])[:40]!r}")
