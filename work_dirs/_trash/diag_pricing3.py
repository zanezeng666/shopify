# -*- coding: utf-8 -*-
"""限量 5 个变体真实推送，看错误明细。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.pricing import PricingService  # noqa: E402

svc = PricingService()
r = svc.recalc_store(store_id=1, dry_run=False, max_updates=5)
for k in ("to_update", "updated", "failed", "unchanged"):
    print(k, r.get(k))
print("errors:", (r.get("errors") or [])[:5])
