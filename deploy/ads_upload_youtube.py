# -*- coding: utf-8 -*-
"""code -> youtube.upload token -> 上传 mp4(unlisted) -> 挂 PMax VIDEO。用法:
python ads_upload_youtube.py "4/0A..."（PowerShell 双引号内贴 code）
"""
import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG_RN = f"customers/{CID}/assetGroups/6770847164"
MP4 = "/home/jason/shopify-admin/deploy/estry_carousel_10s.mp4"
SCOPES = "https://www.googleapis.com/auth/youtube.upload"

CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]

code = sys.argv[1] if len(sys.argv) > 1 else ""
if not code:
    url = ("https://accounts.google.com/o/oauth2/v2/auth"
           f"?client_id={CLIENT_ID}"
           "&redirect_uri=http://localhost:8080/oauth2callback"
           "&response_type=code"
           f"&scope={SCOPES.replace(':', '%3A').replace('/', '%2F')}"
           "&access_type=offline&prompt=consent")
    print("缺 code。授权链接:\n" + url)
    sys.exit(0)

# 1. code -> refresh_token
r = httpx.post("https://oauth2.googleapis.com/token", data={
    "code": code, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
    "redirect_uri": "http://localhost:8080/oauth2callback",
    "grant_type": "authorization_code"}, timeout=30)
r.raise_for_status()
refresh = r.json().get("refresh_token")
print("refresh_token:", "获取成功" if refresh else "未返回(重复授权过?)")
if not refresh:
    sys.exit(1)

# 2. access_token
r2 = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
    "refresh_token": refresh, "grant_type": "refresh_token"}, timeout=30)
r2.raise_for_status()
access = r2.json()["access_token"]

# 2.5 立刻存 refresh_token（code 一次性，防后续失败丢授权）
env_path = "/home/jason/shopify-admin/.env"
env = open(env_path).read()
if "YT_REFRESH_TOKEN" not in env:
    with open(env_path, "a") as fh:
        fh.write(f"YT_REFRESH_TOKEN={refresh}\n")
    print("已存 YT_REFRESH_TOKEN 到 .env")

# 3. 上传 YouTube (multipart: metadata + media)
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
    sys.exit(1)
vid = up.json()["id"]
print("YouTube video_id:", vid)

# 4. Google Ads 挂载
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
q = ("SELECT asset_group.ad_strength FROM asset_group "
     f"WHERE asset_group.resource_name = '{AG_RN}'")
for row in gas.search(customer_id=CID, query=q):
    print("ad_strength:", row.asset_group.ad_strength.name)
