# -*- coding: utf-8 -*-
"""启用 YouTube Data API 后续传：refresh_token(.env) -> 上传 -> 挂 PMax VIDEO。"""
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG_RN = f"customers/{CID}/assetGroups/6770847164"
MP4 = "/home/jason/shopify-admin/deploy/estry_carousel_10s.mp4"
CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
REFRESH = os.environ["YT_REFRESH_TOKEN"]

# 1. access_token
r = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
    "refresh_token": REFRESH, "grant_type": "refresh_token"}, timeout=30)
r.raise_for_status()
access = r.json()["access_token"]
print("access_token: OK")

# 2. 上传 YouTube (multipart: metadata + media)
meta = {"snippet": {
    "title": "Estry Medical Device Batteries - Exact-Fit OEM Replacement",
    "description": "Replacement batteries for patient monitors, defibrillators "
                   "and ventilators. 200+ device models, fast US shipping, "
                   "1-year warranty. https://estrybattery.com",
    "categoryId": "28"},  # Science & Technology
    "status": {"privacyStatus": "unlisted", "selfDeclaredMadeForKids": False}}
boundary = "estryvid7f3a9"
body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
        + json.dumps(meta) + f"\r\n--{boundary}\r\nContent-Type: video/mp4\r\n\r\n"
        ).encode() + open(MP4, "rb").read() + f"\r\n--{boundary}--\r\n".encode()
up = httpx.post(
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=multipart&part=snippet,status",
    headers={"Authorization": f"Bearer {access}",
             "Content-Type": f"multipart/related; boundary={boundary}"},
    content=body, timeout=300)
if up.status_code not in (200, 201):
    print("上传失败:", up.status_code, up.text[:400])
    raise SystemExit(1)
vid = up.json()["id"]
print("YouTube video_id:", vid)

# 3. Google Ads 挂载
from google.ads.googleads.client import GoogleAdsClient  # noqa: E402
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
asset_svc = client.get_service("AssetService")
op = client.get_type("AssetOperation")
op.create.name = "Estry Product Carousel 10s"
op.create.youtube_video_asset.youtube_video_id = vid
res = asset_svc.mutate_assets(customer_id=CID, operations=[op])
rn = res.results[0].resource_name
print("素材创建:", rn)

aga = client.get_service("AssetGroupAssetService")
op2 = client.get_type("AssetGroupAssetOperation")
op2.create.asset_group = AG_RN
op2.create.asset = rn
op2.create.field_type = "VIDEO"
op2.create.status = "ENABLED"
aga.mutate_asset_group_assets(customer_id=CID, operations=[op2])
print("PMax VIDEO 挂载 OK")

gas = client.get_service("GoogleAdsService")
q = ("SELECT asset_group_asset.field_type, asset_group_asset.status "
     "FROM asset_group_asset "
     f"WHERE asset_group_asset.asset_group = '{AG_RN}'")
from collections import Counter  # noqa: E402
cnt = Counter(f"{x.asset_group_asset.field_type.name}/{x.asset_group_asset.status.name}"
              for x in gas.search(customer_id=CID, query=q))
print("Readback:", dict(cnt))
q2 = ("SELECT asset_group.ad_strength FROM asset_group "
      f"WHERE asset_group.resource_name = '{AG_RN}'")
for row in gas.search(customer_id=CID, query=q2):
    print("ad_strength:", row.asset_group.ad_strength.name)
