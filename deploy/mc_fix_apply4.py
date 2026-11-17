# -*- coding: utf-8 -*-
"""MC 清理收尾：Bushnell touch 重推 + v2.1 delete 尝试 + 输出基线。"""
import json
import os
import sys
from collections import defaultdict

import httpx
from dotenv import load_dotenv

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

load_dotenv("/home/jason/shopify-admin/.env")
MID = "136469408"

recs = json.load(open("/home/jason/shopify-admin/deploy/mc_issues_20261116.json"))
seen, uniq = set(), defaultdict(list)
for r in recs:
    for i in r["issues"]:
        k = (r["offerId"], i["code"])
        if k not in seen:
            seen.add(k)
            uniq[i["code"]].append((r, i))

cl = ShopifyRest(StoreService().get_client(1)).client

# 1. Bushnell（active、link 陈旧）：写 category metafield 触发 feed 重推
GPC = {"namespace": "google", "key": "product_category",
       "type": "single_line_text_field", "value": "Hardware > Batteries"}
for r, _ in uniq["landing_page_error"]:
    pid = r["offerId"].split("_")[2]
    p = cl.request("GET", f"products/{pid}.json",
                   params={"fields": "id,status"})
    if p["product"]["status"] == "active":
        cl.request("POST", f"products/{pid}/metafields.json",
                   json_body={"metafield": GPC})
        print(f"touch 重推+category: {pid} (active, link 将随 feed 更新)")
    else:
        print(f"跳过 touch（draft，等 feed 自动撤）: {pid}")

# 2. v2.1 delete 尝试（对 Shopify 集成源大概率不通，试一次）
tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
d = httpx.delete(
    f"https://shoppingcontent.googleapis.com/v2.1/{MID}/products/"
    f"{uniq['landing_page_error'][0][0]['offerId']}",
    headers=H, timeout=30)
print(f"v2.1 delete 探测: HTTP {d.status_code}"
      + (" (将删其余2个)" if d.status_code in (200, 204)
         else " → 放弃手动删，等 feed 自动撤"))

# 3. 基线输出（明日复查对照）
hard = {}
for code in ("item_missing_required_attribute", "guns_parts_policy_violation",
             "landing_page_error", "endangered_species_policy_violation",
             "tobacco_policy_violation", "local_requirements_policy_violation"):
    hard[code] = len(uniq.get(code, []))
base = {"date": "2026-11-16", "free_listing_hard_dis": hard,
        "total": sum(hard.values())}
with open("/home/jason/shopify-admin/deploy/mc_baseline_20261116.json",
          "w") as f:
    json.dump(base, f, ensure_ascii=False, indent=1)
print(f"\n基线已存 deploy/mc_baseline_20261116.json: {base['total']} 个硬dis")
