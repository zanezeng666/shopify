# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.pricing import PricingService
st = PricingService().run_all_stores(dry_run=False)
d = st["decisions"]
print("done:", {k: d[k] for k in ("priced", "total", "stopped")})
for s in st["stores"]:
    if "error" in s:
        print("store", s["store_id"], "ERR", s["error"][:100])
    else:
        r = s["recalc"]
        print("store", s["store_id"], "updated:", r["updated"], "/", r["to_update"], "failed:", r.get("failed"))
