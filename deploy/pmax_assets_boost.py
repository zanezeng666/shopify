# -*- coding: utf-8 -*-
"""PMax 素材挂载（asset 已创建，按 name 查 resource_name）→ readback。"""
import os

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = f"customers/{CID}/assetGroups/6770847164"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

# 1) 按 name 查 5 个图片 asset + 查文本/CTA asset（text 查询）
names = ["Estry Medical Wide A", "Estry Medical Wide B",
         "Estry Medical Tall A", "Estry Medical Tall B",
         "Estry Logo Square"]
found = {}
for n in names:
    rows = gas.search(customer_id=CID, query=(
        f"SELECT asset.resource_name FROM asset WHERE asset.name = '{n}'"))
    hits = [r.asset.resource_name for r in rows]
    if hits:
        found[n] = hits[0]
print("图片 asset:", len(found), "/", len(names))

rows = gas.search(customer_id=CID, query=(
    "SELECT asset.resource_name FROM asset "
    "WHERE asset.text_asset.text = 'EstryBattery'"))
bn = [r.asset.resource_name for r in rows]
rows = gas.search(customer_id=CID, query=(
    "SELECT asset.resource_name FROM asset "
    "WHERE asset.call_to_action_asset.call_to_action = 'SHOP_NOW'"))
cta = [r.asset.resource_name for r in rows]
print("business_name:", bn, " cta:", cta)

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json",
     "developer-token": "unused"}

pairs = [(found["Estry Medical Wide A"], "MARKETING_IMAGE"),
         (found["Estry Medical Wide B"], "MARKETING_IMAGE"),
         (found["Estry Medical Tall A"], "PORTRAIT_MARKETING_IMAGE"),
         (found["Estry Medical Tall B"], "PORTRAIT_MARKETING_IMAGE"),
         (found["Estry Logo Square"], "LOGO"),
         (bn[0], "BUSINESS_NAME"),
         (cta[0], "CALL_TO_ACTION_SELECTION")]

# 2) 挂载（逐个独立 mutate，一个失败不影响其他）
for asset, ft in pairs:
    r2 = httpx.post(
        f"https://googleads.googleapis.com/v26/customers/{CID}"
        "/assetGroupAssets:mutate", headers=H,
        json={"operations": [{"create": {
            "assetGroup": AG, "asset": asset, "fieldType": ft}}]},
        timeout=120)
    print(f"link {ft:<26} {'OK' if r2.status_code == 200 else r2.text[:120]}")

# 3) readback
rows = gas.search(customer_id=CID, query=(
    "SELECT asset_group.ad_strength, asset_group_asset.field_type "
    "FROM asset_group_asset WHERE campaign.status='ENABLED'"))
from collections import Counter
c = Counter()
strength = ""
for r3 in rows:
    c[r3.asset_group_asset.field_type.name] += 1
    strength = r3.asset_group.ad_strength.name
print("\nreadback strength:", strength)
for t, n in sorted(c.items()):
    print(f"  {t} x{n}")
