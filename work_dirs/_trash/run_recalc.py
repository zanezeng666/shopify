# -*- coding: utf-8 -*-
"""定价全量重算：dry_run 预览 → 差异显著才真跑。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.pricing import PricingService  # noqa: E402

svc = PricingService()
st = svc.run_all_stores(dry_run=True)
d = st["decisions"]
print("dry:", {k: d[k] for k in ("priced", "total", "stopped", "no_cost", "margin_risk")},
      "basis:", d["basis"])
for s in st["stores"]:
    if "error" in s:
        print("store", s["store_id"], "ERR", s["error"][:100])
    else:
        print("store", s["store_id"], "to_update:", s["recalc"]["to_update"],
              "updated:", s["recalc"]["updated"],
              "delist:", s.get("delist", {}))
