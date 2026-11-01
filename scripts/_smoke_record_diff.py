# -*- coding: utf-8 -*-
"""记录级对账真实库冒烟（纯只读）。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shopify_admin.services.products.sync_shopify import CsShopifySyncService

svc = CsShopifySyncService()
d = svc.diff(1, sample=3)
print("cs_catalog:", d["cs_catalog"])
print("store_side:", d["store_side"])
p = d["plan"]
print("to_create=%d to_update=%d archive=%d orphan=%d brand_mismatch=%d unchanged=%d"
      % (p["to_create"]["count"], p["to_update"]["count"], p["to_archive"]["count"],
         p["orphans"]["count"], p["brand_mismatch"]["count"], p["unchanged"]))
print("barcode: fill=%d conflict=%d | price drift=%d suspicious=%d"
      % (p["to_update"]["barcode_fill"], p["to_update"]["barcode_conflict"],
         d["price_report"]["drift_count"], d["price_report"]["suspicious_count"]))
print("\ncreate sample:")
print(json.dumps(p["to_create"]["items"], ensure_ascii=False, indent=1))
print("\nmismatch sample:", json.dumps(p["brand_mismatch"]["items"][:5], ensure_ascii=False))
print("archive sample:", json.dumps(p["to_archive"]["items"][:3], ensure_ascii=False))
