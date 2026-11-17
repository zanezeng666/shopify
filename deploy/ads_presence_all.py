# -*- coding: utf-8 -*-
"""1) 全部 ENABLED campaign 的 positiveGeoTargetType 改 PRESENCE（仅实际在美国的人）
2) 打印 GA4 提权（analytics.edit）OAuth 授权 URL
"""
import os
import urllib.parse

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
camps = list(gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name FROM campaign "
    "WHERE campaign.status = 'ENABLED'")))
print(f"ENABLED campaign: {len(camps)} 个")

tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
     "developer-token": "unused"}

ok = fail = 0
for r in camps:
    c = r.campaign
    resp = httpx.post(
        f"https://googleads.googleapis.com/v26/customers/{CID}/campaigns:mutate",
        headers=H, json={"operations": [{
            "update": {
                "resourceName": c.resource_name,
                "geoTargetTypeSetting": {"positiveGeoTargetType": "PRESENCE"}},
            "updateMask": "geoTargetTypeSetting.positiveGeoTargetType"}]},
        timeout=60)
    if resp.status_code == 200:
        ok += 1
    else:
        fail += 1
        print(f"  FAIL {c.name}: {resp.text[:150]}")
print(f"PRESENCE 改写: {ok} 成功 / {fail} 失败")

# GA4 提权授权 URL（增量授权：保留现有 4 个 scope，新增 analytics.edit）
params = {
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "redirect_uri": "http://localhost:1",
    "response_type": "code",
    "scope": "https://www.googleapis.com/auth/analytics.edit",
    "access_type": "offline",
    "prompt": "consent",
    "include_granted_scopes": "true",
}
print("\n=== GA4 提权授权链接（浏览器打开，登录 Google 账号并点同意）===")
print("https://accounts.google.com/o/oauth2/v2/auth?"
      + urllib.parse.urlencode(params))
