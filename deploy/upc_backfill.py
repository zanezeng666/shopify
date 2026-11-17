# -*- coding: utf-8 -*-
"""UPC 回填: estry_upc_map(status=2 GEPIR过/用户确认官方) -> Shopify barcode。

用法:
  python upc_backfill.py           # 回填全部 status>=2 且未回填的
  python upc_backfill.py --mark-ok # 用户确认GS1官方直购, 批量置 status=2
"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import get_engine
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

eng = get_engine()

if "--mark-ok" in sys.argv:
    with eng.begin() as conn:
        n = conn.execute(text(
            "UPDATE estry_upc_map SET status=2 WHERE status=1")).rowcount
    print(f"已置 status=2(GEPIR过/官方确认): {n} 条")
    sys.exit(0)

cl = ShopifyRest(StoreService().get_client(1)).client

# 1) 拉全店 sku->variant_id (复核映射)
params = {"limit": 250, "status": "active", "fields": "id,variants"}
sku2vid = {}
while True:
    time.sleep(0.9)
    r = cl._client.get("products.json", params=params, auth=cl._auth,
                       timeout=60)
    r.raise_for_status()
    for p in r.json()["products"]:
        for v in p["variants"]:
            if v.get("sku"):
                sku2vid[v["sku"]] = v["id"]
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1],
              "fields": "id,variants"}
print(f"变体 SKU 映射: {len(sku2vid)}")

# 2) 取待回填清单
with eng.begin() as conn:
    conn.execute(text("""
    UPDATE estry_upc_map SET variant_id = :vid WHERE sku = :sku
    """), [{"vid": sku2vid[s], "sku": s}
           for s in set(r[0] for r in conn.execute(
               text("SELECT sku FROM estry_upc_map WHERE status>=2"))
               ) if s in sku2vid])
rows = None
with eng.begin() as conn:
    rows = conn.execute(text(
        "SELECT variant_id, upc FROM estry_upc_map "
        "WHERE status=2 AND variant_id>0")).fetchall()
print(f"待回填: {len(rows)}")

# 3) 逐个写入 barcode
ok = fail = 0
for i, (vid, upc) in enumerate(rows, 1):
    for attempt in range(3):
        try:
            time.sleep(0.45)
            r2 = cl._client.put(f"variants/{vid}.json", auth=cl._auth,
                                json={"variant": {"id": vid,
                                                  "barcode": upc}},
                                timeout=30)
            r2.raise_for_status()
            ok += 1
            with eng.begin() as conn:
                conn.execute(text(
                    "UPDATE estry_upc_map SET status=3 WHERE variant_id=:v"),
                    [{"v": vid}])
            break
        except Exception as ex:
            if attempt == 2:
                fail += 1
                print(f"FAIL {vid} {upc} {str(ex)[:80]}", flush=True)
            else:
                time.sleep(2 ** attempt)
    if i % 500 == 0:
        print(f"进度 {i}/{len(rows)} ok={ok} fail={fail}", flush=True)

print(f"回填完成: ok={ok} fail={fail}")
