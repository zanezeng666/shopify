# -*- coding: utf-8 -*-
"""全量分布统计：普通组 vs 巨组(>8页)，及巨组清单。"""
import os
import sys
from collections import defaultdict

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
cc.execute("SELECT cs_id, part_no, fit_model, capacity FROM cs_product")
groups = defaultdict(list)
for cs_id, pn, fm, cap in cc.fetchall():
    if pn and fm:
        groups[(pn, fm)].append((cs_id, cap))
cs.close()
csid2cap, gid_of = {}, {}
for gi, (k, mem) in enumerate(groups.items()):
    for cs_id, cap in mem:
        csid2cap[cs_id] = cap
        gid_of[cs_id] = gi

cl = ShopifyRest(StoreService().get_client(1)).client
params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,title,handle,status,variants", "status": "active"}
live = []
while True:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    live += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>") for x in link.split(",")
           if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

agg = defaultdict(list)
for p in live:
    v = (p["variants"] or [{}])[0]
    cs_id = (v.get("sku") or "").split("_")[0]
    gi = gid_of.get(cs_id)
    if gi is not None:
        agg[gi].append((p["id"], p["title"], csid2cap.get(cs_id)))

normal, big, done_gids = [], [], set()
# 排除试点已完成的组（主品多变体的）
for p in live:
    pass  # 试点组通过变体数>1识别比较绕，直接按 cs_id 分组排除

merge = []
for gi, mem in agg.items():
    caps = {c for _, _, c in c if c} if False else {c for _, _, c in mem if c}
    if len(mem) >= 2 and len(caps) >= 2:
        merge.append((gi, mem))

big = [(gi, m) for gi, m in merge if len(m) > 8]
normal = [(gi, m) for gi, m in merge if len(m) <= 8]
print(f"普通组(<=8页): {len(normal)} | 涉及 {sum(len(m) for _, m in normal)} 品"
      f" | 减页 {sum(len(m)-1 for _, m in normal)}")
print(f"巨组(>8页): {len(big)} | 涉及 {sum(len(m) for _, m in big)} 品"
      f" | 减页 {sum(len(m)-1 for _, m in big)}")
for gi, m in sorted(big, key=lambda x: -len(x[1]))[:12]:
    print(f"  [{len(m)}页] {m[0][1][:60]}")
