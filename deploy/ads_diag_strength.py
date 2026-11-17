# -*- coding: utf-8 -*-
"""诊断 PMax 广告效力：素材类型分布/数量/文本长度/图片比例。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = 6770847164

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

# 1. 当前效力分
q0 = ("SELECT asset_group.ad_strength FROM asset_group "
      f"WHERE asset_group.resource_name = 'customers/{CID}/assetGroups/{AG}'")
for r in gas.search(customer_id=CID, query=q0):
    print(f"当前 ad_strength = {r.asset_group.ad_strength.name}\n")

# 2. 素材分布
q = ("SELECT asset_group_asset.asset, asset_group_asset.field_type, "
     "asset_group_asset.status "
     "FROM asset_group_asset "
     f"WHERE asset_group_asset.asset_group = 'customers/{CID}/assetGroups/{AG}' "
     "AND asset_group_asset.status = 'ENABLED'")
rows = list(gas.search(customer_id=CID, query=q))
print(f"ENABLED 素材: {len(rows)}")

# 3. 批量取 asset 详情
rn = [str(r.asset_group_asset.asset) for r in rows]
info = {}
B = 90
for i in range(0, len(rn), B):
    chunk = ", ".join(f"'{x}'" for x in rn[i:i + B])
    qa = ("SELECT asset.resource_name, asset.type, asset.text_asset.text, "
          "asset.image_asset.full_size.width_pixels, "
          "asset.image_asset.full_size.height_pixels, asset.name "
          f"FROM asset WHERE asset.resource_name IN ({chunk})")
    for a in gas.search(customer_id=CID, query=qa):
        info[str(a.asset.resource_name)] = a.asset

buckets = {}
for r in rows:
    ft = r.asset_group_asset.field_type.name
    a = info.get(str(r.asset_group_asset.asset))
    if a is None:
        buckets.setdefault(ft, []).append(("?", "?"))
        continue
    if a.type_.name == "TEXT":
        txt = a.text_asset.text or ""
        buckets.setdefault(ft, []).append((f"TEXT({len(txt)}字)", txt[:60]))
    elif a.type_.name == "IMAGE":
        w = a.image_asset.full_size.width_pixels
        h = a.image_asset.full_size.height_pixels
        ratio = f"{w}x{h}({round(w/h, 2) if h else '?'})"
        buckets.setdefault(ft, []).append((f"IMG {ratio}", (a.name or "")[:40]))
    else:
        buckets.setdefault(ft, []).append((a.type_.name, a.name or ""))

LIMITS = {"HEADLINE": 15, "LONG_HEADLINE": 5, "DESCRIPTION": 5,
          "IMAGE": 20, "VIDEO": 5, "BUSINESS_NAME": 1,
          "LOGO": 5, "CALL_TO_ACTION_ASSET": 1, "PRICE_ASSET": 1,
          "PROMOTION_ASSET": 1}
for ft in sorted(buckets):
    n = len(buckets[ft])
    lim = LIMITS.get(ft.split("_ASSET")[0], "?")
    print(f"\n[{ft}] {n}/{lim}")
    for k, v in buckets[ft]:
        print(f"  {k:16} {v}")
