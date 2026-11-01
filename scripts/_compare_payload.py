# -*- coding: utf-8 -*-
"""对照材料：引擎将创建的新品完整 payload vs 店铺已有老产品（本地镜像），纯只读。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select

from shopify_admin.core.database import session_scope
from shopify_admin.models.product import Product
from shopify_admin.services.products.sync_shopify import CsShopifySyncService

svc = CsShopifySyncService()

# 1) 店铺已有老产品（本地镜像同步自 Shopify）
with session_scope() as s:
    cols = [c.name for c in Product.__table__.columns]
    olds = s.execute(
        select(Product).where(Product.store_id == 1).order_by(Product.id.desc()).limit(3)
    ).scalars().all()
print("Product columns:", cols)
for p in olds:
    d = {c: getattr(p, c) for c in cols}
    for k in ("raw", "created_at", "updated_at"):
        d.pop(k, None)
    print("\n===== 老产品（店铺现有）=====")
    print(json.dumps(d, ensure_ascii=False, indent=1, default=str)[:2500])

# 2) 引擎将创建的新品完整 payload（真实 CS 数据）
cat = svc.load_cs_catalog()
diff = svc.diff(1, sample=3)
print("\n\n########## 引擎将创建的新品完整 payload（前3个）##########")
for it in diff["plan"]["to_create"]["items"][:3]:
    full = svc.build_new_product_payload(cat[it["cs_id"]])
    print("\n===== 新品", it["cs_id"], "=====")
    print(json.dumps(full, ensure_ascii=False, indent=1))
