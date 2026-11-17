# -*- coding: utf-8 -*-
"""账号级 primary_for_goal 清洗：
关掉无数据流的 Android installs / UA Transactions，
保留真购买（Google Shopping App Purchase / GA4 purchase）。"""
import os

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
TARGETS = {"Android installs (all other apps)", "Transactions (全部网站数据)"}

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")
rows = gas.search(customer_id=CID, query=(
    "SELECT conversion_action.resource_name, conversion_action.name "
    "FROM conversion_action"))
hits = [r.conversion_action for r in rows
        if r.conversion_action.name in TARGETS]
print("目标动作:", [(c.name, c.resource_name) for c in hits])

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json",
     "developer-token": "unused"}

for c in hits:
    r = httpx.post(
        f"https://googleads.googleapis.com/v26/customers/{CID}"
        "/conversionActions:mutate",
        headers=H, json={"operations": [{
            "update": {"resourceName": c.resource_name,
                       "primaryForGoal": False},
            "updateMask": "primary_for_goal"}]}, timeout=60)
    print(f"  {c.name[:36]:<36} -> primary=False : {r.status_code}"
          + ("" if r.status_code == 200 else " " + r.text[:120]))

# readback：剩余 ENABLED primary=True 清单
rows2 = gas.search(customer_id=CID, query=(
    "SELECT conversion_action.name, conversion_action.primary_for_goal "
    "FROM conversion_action"))
print("\nENABLED 且 primary=True 的动作（应只剩真购买）:")
for r in rows2:
    ca = r.conversion_action
    if ca.primary_for_goal:
        print("  -", ca.name)
