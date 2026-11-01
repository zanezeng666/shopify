# -*- coding: utf-8 -*-
"""单点真实建品：CS-TVR500VX（dry_run 参数化）。用法: uv run python scripts/_apply_one.py [real]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shopify_admin.services.products.sync_shopify import CsShopifySyncService

TARGET = "CS-TVR500VX"
real = len(sys.argv) > 1 and sys.argv[1] == "real"

svc = CsShopifySyncService()
r = svc.apply(1, dry_run=not real, publish_status="draft", only_cs_id=TARGET)
print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
if not real:
    d = svc.diff(1, sample=None)
    rows = [i for i in d["plan"]["to_create"]["items"] if i["cs_id"] == TARGET]
    print(f"\n计划创建 {len(rows)} 个产品，前 4 个:")
    print(json.dumps(rows[:4], ensure_ascii=False, indent=1))
