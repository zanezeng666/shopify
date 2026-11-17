# -*- coding: utf-8 -*-
"""1) 拉在线 disapproved SKU 明细（排除 local inventory 假阳性）
2) PMax asset group 素材现状盘点（field_type 统计+文本内容）。"""
import os
from collections import Counter, defaultdict

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
MID = "136469408"
CID = "7059800494"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}"}

SKIP_MC = True
if not SKIP_MC:
    print("=== 在线 disapproved SKU 明细 ===")
    tok = None
    while True:
        params = {"maxResults": 250}
        if tok:
            params["pageToken"] = tok
        p = httpx.get(
            f"https://shoppingcontent.googleapis.com/content/v2.1/{MID}"
            "/productstatuses", headers=H, params=params, timeout=60)
        if p.status_code != 200:
            print(f"(分页终止: {p.status_code})")
            break
        for it in p.json().get("resources", []):
            online_bad = []
            for ils in it.get("itemLevelIssues", []):
                if ils.get("servability") == "disapproved" and \
                        "local inventory" not in ils.get("description", "").lower():
                    online_bad.append(ils.get("description", "?"))
            if online_bad:
                print(f"  {it.get('title', '?')[:52]:<52} "
                      f"{','.join(set(online_bad))[:46]}")
        tok = p.json().get("nextPageToken")
        if not tok:
            break

# PMax 素材盘点
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

ags = gas.search(customer_id=CID, query=(
    "SELECT asset_group.id, asset_group.name, asset_group.ad_strength "
    "FROM asset_group WHERE campaign.status='ENABLED'"))
for r in ags:
    print(f"\n=== asset_group id={r.asset_group.id} "
          f"{r.asset_group.name} strength={r.asset_group.ad_strength.name}")

rows = gas.search(customer_id=CID, query=(
    "SELECT asset_group_asset.field_type, asset_group_asset.status, "
    "asset.text_asset.text, asset.image_asset.full_size.url "
    "FROM asset_group_asset WHERE campaign.status='ENABLED'"))
by_type = defaultdict(list)
for r in rows:
    aga = r.asset_group_asset
    label = (r.asset.text_asset.text or
             (r.asset.image_asset.full_size.url[:60] if
              r.asset.image_asset.full_size.url else "?"))
    by_type[aga.field_type.name].append(label)
for t, items in sorted(by_type.items()):
    print(f"\n[{t}] x{len(items)}")
    for i in items[:8]:
        print(f"   - {i[:70]}")
