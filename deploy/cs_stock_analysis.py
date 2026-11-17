# -*- coding: utf-8 -*-
"""医疗热销终榜: 库存扣减(累计) × 10天订单(近期) 双指标
→ 映射 medical-battery collection 的 Shopify 产品 → 视频换图推荐。
"""
import sys
import time
from collections import defaultdict

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import (  # noqa: E402
    get_cs_engine, get_engine,
)
from dotenv import load_dotenv  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

load_dotenv("/home/jason/shopify-admin/.env")

# --- 1. 双指标原始分 ---
stock_score = {}   # part_no_prefix -> 累计扣减（含补货量修正: 扣减+补货=真实出货下限）
with get_cs_engine().connect() as c:
    rows = c.execute(text("""
        SELECT MAX(p.part_no) part, SUM(-l.change_qty) dec_t,
               SUM(CASE WHEN l.change_qty>0 THEN l.change_qty ELSE 0 END) inc_t
        FROM cs_inventory_log l JOIN cs_product p ON p.cs_id=l.cs_id
        WHERE p.category='Medical' AND l.change_qty<>0
        GROUP BY p.cs_id ORDER BY dec_t DESC
    """)).fetchall()
    for part, dec, inc in rows:
        if part:
            stock_score[str(part)] = (dec or 0, inc or 0)
print(f"医疗库存变化产品: {len(stock_score)}")

order_score = defaultdict(int)  # part -> 近10天销量
with get_engine().connect() as m:
    rows = m.execute(text("""
        SELECT oi.sku, SUM(oi.quantity) q
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE oi.created_at >= '2026-10-30'
          AND o.cancelled_at IS NULL AND oi.sku LIKE 'CS-%'
        GROUP BY oi.sku
    """)).fetchall()
for sku, q in rows:
    part = sku.split("_")[0][3:]  # CS-XXX_... -> XXX
    order_score[part] += q
print(f"订单涉及 part: {len(order_score)}")

# --- 2. 综合: 订单10天销量*4(月化权重) + 库存累计扣减 ---
combo = {}
for part, (dec, inc) in stock_score.items():
    combo[part] = {"stock_dec": dec, "stock_inc": inc,
                   "order10": order_score.get(part, 0)}
for part, q in order_score.items():
    if part not in combo:
        combo[part] = {"stock_dec": 0, "stock_inc": 0, "order10": q}
for part, v in combo.items():
    v["score"] = v["order10"] * 4 + v["stock_dec"]

top = sorted(combo.items(), key=lambda x: -x[1]["score"])[:20]

# --- 3. 映射 Shopify 医疗 collection 产品 ---
cl = ShopifyRest(StoreService().get_client(1)).client
prods = []
cursor = None
Q = """
query($c: String!, $after: String) {
  collectionByHandle(handle: $c) {
    products(first: 100, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { legacyResourceId title
              variants(first: 60) { nodes { sku } } }
    }
  }
}
"""
while True:
    r = cl.graphql(Q, {"c": "medical-battery", "after": cursor})
    conn = r["collectionByHandle"]["products"]
    for n in conn["nodes"]:
        p = {"id": int(n["legacyResourceId"]), "title": n["title"],
             "variants": [{"sku": v["sku"]}
                          for v in n["variants"]["nodes"]]}
        prods.append(p)
    if not conn["pageInfo"]["hasNextPage"]:
        break
    cursor = conn["pageInfo"]["endCursor"]
    time.sleep(0.4)
print(f"medical-battery collection 产品: {len(prods)}")

pid_by_part = {}
for p in prods:
    for v in p.get("variants", []):
        sku = v.get("sku") or ""
        if sku.startswith("CS-"):
            pid_by_part[sku.split("_")[0][3:]] = p

print("\n=== 医疗热销综合榜 TOP20 (近期订单×4 + 累计库存扣减) ===")
print(f"{'part_no':26} {'10天单':>6} {'累计扣':>6} {'补货':>5} score"
      "  Shopify产品")
hit = 0
for part, v in top:
    p = pid_by_part.get(part)
    t = (p["title"][:46] + f" [P{p['id']}]") if p else "—不在collection—"
    if p:
        hit += 1
    print(f"{part[:26]:26} {v['order10']:>6} {v['stock_dec']:>6} "
          f"{v['stock_inc']:>5} {v['score']:>6}  {t}")
print(f"\ncollection 命中: {hit}/{len(top)}")
