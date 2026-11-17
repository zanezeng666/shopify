# -*- coding: utf-8 -*-
"""统计: Google渠道收录数 + active产品状态 + 类目分布 + 医疗类目产品数。"""
import sys
import time
import json

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

OUT = "/tmp/status_stats_out.json"
cl = ShopifyRest(StoreService().get_client(1)).client

# 1) Google channel 产品收录数(publication products 翻页计数)
r = cl._client.post(
    f"{cl._client.base_url}/graphql.json", auth=cl._auth,
    json={"query": "{ publications(first: 20) { nodes { id name } } }"},
    timeout=60)
pubs = r.json()["data"]["publications"]["nodes"]
gpub = next((p for p in pubs if "google" in p["name"].lower()), None)
g_count = None
if gpub:
    q = ("query($id:ID!,$n:Int!,$c:String){publication(id:$id){"
         "products(first:$n,after:$c){pageInfo{hasNextPage endCursor}"
         "nodes{id}}}}")
    after, g_count = None, 0
    while True:
        r = cl._client.post(
            f"{cl._client.base_url}/graphql.json", auth=cl._auth,
            json={"query": q, "variables": {"id": gpub["id"], "n": 250,
                                            "c": after}}, timeout=60)
        d = r.json()["data"]["publication"]["products"]
        g_count += len(d["nodes"])
        if not d["pageInfo"]["hasNextPage"]:
            break
        after = d["pageInfo"]["endCursor"]
        time.sleep(0.45)
print(f"Google渠道在列: {gpub['name'] if gpub else '缺失'}, 收录产品: {g_count}")

# 2) 全量 active 产品统计
MEDICAL_KW = [
    "medical", "wheelchair", "hearing aid", "hearingaid", "patient monitor",
    "defibrillator", "infusion", "ventilator", "respirator", "blood pressure",
    "oximeter", "ecg", "ekg", "ultrasound", "x-ray", "dental", "surgical",
    "hospital", "clinic", "nurse", "vital sign", "emr", "endoscope",
]
total = 0
no_bc = 0
has_bc = 0
type_dist = {}
med_products = []
params = {"limit": 250, "status": "active",
          "fields": "id,title,product_type,tags,variants"}
while True:
    r = cl._client.get("products.json", auth=cl._auth,
                       params=params, timeout=60)
    items = r.json().get("products", [])
    if not items:
        break
    for p in items:
        total += 1
        bc_any = any(v.get("barcode") for v in p.get("variants", []))
        if bc_any:
            has_bc += 1
        else:
            no_bc += 1
        t = (p.get("product_type") or "未分类").strip() or "未分类"
        type_dist[t] = type_dist.get(t, 0) + 1
        hay = " ".join([
            p.get("title") or "", t, " ".join(p.get("tags", []))
        ]).lower()
        if any(k in hay for k in MEDICAL_KW):
            med_products.append({
                "id": p["id"], "title": p["title"][:70], "type": t})
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1],
              "fields": "id,title,product_type,tags,variants"}
    time.sleep(0.45)
    if total % 2500 == 0:
        print(f"  已扫 {total} 品...")

top_types = sorted(type_dist.items(), key=lambda x: -x[1])[:20]
result = {
    "google_pub_count": g_count,
    "active_total": total,
    "barcode_cleared": no_bc,
    "barcode_remaining": has_bc,
    "type_top20": top_types,
    "medical_count": len(med_products),
    "medical_type_dist": sorted(
        {m["type"] for m in med_products}),
    "medical_samples": med_products[:15],
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print(json.dumps(result, ensure_ascii=False, indent=1)[:3000])
print("DONE ->", OUT)
