# -*- coding: utf-8 -*-
"""分诊 backfill_stock 538 个 404 失败 SKU。

假设：404 = 镜像中同 csid 存在"旧产品孪生"（远端已删、镜像残留 active），
其 inventory_item_id 已死；launch_new 昨日重建的新品是另一行，库存已推成功。
验证：①镜像行分布（同 SKU 挂几个产品行）②远端按 SKU 查：qty>0=无害孪生，
qty=0=新品存在但库存没推上（需补），remote_missing=远端整品不存在（需查）。
"""
import re
import sys
import json
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text, bindparam  # noqa: E402
from shopify_admin.core.database import session_scope  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

LOG = "/tmp/backfill_go.log"
OUT = "/home/jason/shopify-admin/deploy/backfill_fail_diag_20261114.json"

fails = []
for line in open(LOG, encoding="utf-8", errors="replace"):
    m = re.search(r"sku=([A-Za-z0-9_.\-]+):", line)
    if m and "404" in line:
        fails.append(m.group(1))
uniq = list(dict.fromkeys(fails))
print("fail_lines", len(fails), "uniq_skus", len(uniq), flush=True)

# 1) 镜像行分布
info = {}
stmt = text(
    "SELECT pv.sku, pv.id AS vid, p.id AS pid, p.created_at, p.status "
    "FROM product_variants pv JOIN products p ON p.id = pv.product_id "
    "WHERE pv.store_id = 1 AND pv.sku IN :sk "
    "ORDER BY pv.sku, p.created_at"
).bindparams(bindparam("sk", expanding=True))
with session_scope() as s:
    for i in range(0, len(uniq), 200):
        for sku, vid, pid, cat, st in s.execute(stmt, {"sk": uniq[i:i + 200]}).all():
            info.setdefault(sku, []).append(
                {"vid": vid, "pid": pid, "created": str(cat), "status": st})

dup = [x for x in uniq if len(info.get(x, [])) >= 2]
single = [x for x in uniq if len(info.get(x, [])) == 1]
norow = [x for x in uniq if not info.get(x)]
print("mirror: dup_product", len(dup), "| single_row", len(single),
      "| no_row", len(norow), flush=True)
old_d = Counter(min(r["created"] for r in info[x])[:10] for x in dup)
new_d = Counter(max(r["created"] for r in info[x])[:10] for x in dup)
print("dup_oldest_created", dict(old_d.most_common(6)), flush=True)
print("dup_newest_created", dict(new_d.most_common(6)), flush=True)

# 2) 远端逐 SKU 核查
q = ("query($q:String!){productVariants(first:3,query:$q){edges{node{"
     "sku inventoryQuantity product{status}}}}}")
cl = ShopifyRest(StoreService().get_client(1)).client
remote = {}
live_ok = live_zero = missing = errs = 0
for i, sku in enumerate(uniq):
    try:
        r = cl.graphql(q, {"q": f"sku:{sku}"})
        edges = ((r or {}).get("productVariants") or {}).get("edges") or []
        nodes = [e["node"] for e in edges
                 if (e.get("node") or {}).get("sku") == sku]
        if not nodes:
            missing += 1
            remote[sku] = "remote_missing"
        else:
            qty = sum(int(n.get("inventoryQuantity") or 0) for n in nodes)
            remote[sku] = {"qty": qty, "pstatus": nodes[0].get("product", {}).get("status"),
                           "n": len(nodes)}
            if qty > 0:
                live_ok += 1
            else:
                live_zero += 1
    except Exception as e:  # noqa: BLE001
        errs += 1
        remote[sku] = f"ERR {e}"
    if i % 100 == 99:
        print(f"  remote {i + 1}/{len(uniq)} ok={live_ok} zero={live_zero} "
              f"miss={missing} err={errs}", flush=True)

print("REMOTE: qty>0(harmless_twin)", live_ok, "| qty=0(NEED_RETRY)", live_zero,
      "| remote_missing", missing, "| errors", errs, flush=True)
zero_skus = [x for x in uniq if isinstance(remote.get(x), dict) and remote[x]["qty"] == 0]
print("zero_sku_sample", zero_skus[:15], flush=True)
miss_skus = [x for x in uniq if remote.get(x) == "remote_missing"]
print("missing_sku_sample", miss_skus[:15], flush=True)

json.dump({"failed_skus": uniq, "mirror": info, "remote": remote},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved", OUT, flush=True)
