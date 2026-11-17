# -*- coding: utf-8 -*-
"""落盘 819 孤儿变体清单（cs_id 分布+建议），供镜像清理决策。"""
import json
import re
import sys
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.pricing import PricingService  # noqa: E402

svc = PricingService()
dec = svc.build_decisions()
_CS = re.compile(r"^(CS-[A-Za-z0-9]+)")

orphans = []
for vid, sku, cur in svc._variant_cs_ids(1):
    m = _CS.match(sku or "")
    if not m:
        continue
    d = dec.get(m.group(1))
    if d is None or d.price is None or d.stopped:
        continue
    if cur is not None and abs(float(cur) - d.price) < 0.005:
        continue
    orphans.append({"vid": vid, "sku": sku, "cur": float(cur or 0), "target": float(d.price)})

cnt = Counter(s["_CS"] if False else s["sku"].split("_")[0] for s in orphans)
out = {"total": len(orphans), "by_cs_prefix_top20": cnt.most_common(20),
       "note": "远端产品已删除（REST 404 实证），本地镜像孤儿记录；定价引擎已自动跳过（无害）",
       "samples": orphans[:30]}
with open("/home/jason/shopify-admin/deploy/pricing_orphans_20261113.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("total orphans:", len(orphans))
print("top:", cnt.most_common(8))
