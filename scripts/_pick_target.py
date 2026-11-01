# -*- coding: utf-8 -*-
"""挑选真实建品目标：多品牌 cs_id，部分品牌已上架（可新老对比）+ 其余在 to_create（只读）。"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shopify_admin.services.products.sync_shopify import CsShopifySyncService

svc = CsShopifySyncService()
d = svc.diff(1, sample=None)
items = d["plan"]["to_create"]["items"]

catalog = svc.load_cs_catalog()
by_cs = {}
for (csid, bl), row in catalog.items():
    by_cs.setdefault(csid, {})[bl] = row

# 店铺已上架变体的 csid（用于挑"部分已上架"的目标）
anchored_csids = set()
with open(Path(__file__).parent / "_pick_target_hint.txt", "w", encoding="utf-8") as _:
    pass

create_by_csid = Counter(i["cs_id"] for i in items)
cands = []
for csid, n_create in create_by_csid.items():
    recs = by_cs.get(csid) or {}
    if len(recs) < 2 or n_create < 1:
        continue
    # 记录质量：字段齐全分
    filled = sum(1 for r in recs.values()
                 if r["fit_model"] and r["bar_code"] and r["retail"] and r["gross_weight_g"])
    # 店铺已有该 csid 的其他变体（matched→update，即部分品牌已上架）
    import re
    has_existing = any(re.match(r"^(CS-[A-Za-z0-9]+)", i["sku"] or "").group(1) == csid
                       for i in d["plan"]["to_update"]["items"])
    # 全部品牌都要创建（完整多品牌建品演示）or 部分已上架
    cands.append((csid, len(recs), n_create, filled, has_existing,
                  sorted(r["brand"] for r in recs.values())))

cands.sort(key=lambda x: (-x[4], -x[3], -x[2]))
print("csid | 品牌数 | 待建数 | 字段齐全分 | 有存量 | 品牌列表")
for c in cands[:12]:
    print(" ", c[0], "|", c[1], "|", c[2], "|", c[3], "|", c[4], "|", ", ".join(c[5][:6]))
