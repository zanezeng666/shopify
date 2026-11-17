# -*- coding: utf-8 -*-
"""1) 摘除 GA4 key event '浏览超1分钟'（源头清洗，可逆）
2) 查 Ads 侧 GA4 来源转化动作列表（看 generate_lead 是否已同步）"""
import os

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
PROPERTY = "313397200"
CID = "7059800494"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
URL = (f"https://analyticsadmin.googleapis.com/v1alpha/properties/{PROPERTY}"
       "/keyEvents")

kes = httpx.get(URL, headers=H, timeout=30).json().get("keyEvents", [])
print("当前 key events:", [k["eventName"] for k in kes])
for k in kes:
    if k["eventName"] == "浏览超1分钟":
        d = httpx.delete(
            f"https://analyticsadmin.googleapis.com/v1alpha/{k['name']}",
            headers=H, timeout=30)
        print("摘除 浏览超1分钟:", d.status_code, d.text[:120])
final = httpx.get(URL, headers=H, timeout=30).json().get("keyEvents", [])
print("最终 key events:", [k["eventName"] for k in final])

# Ads 侧 GA4 来源转化动作
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")
rows = gas.search(customer_id=CID, query=(
    "SELECT conversion_action.id, conversion_action.name, "
    "conversion_action.category, conversion_action.status, "
    "conversion_action.primary_for_goal, conversion_action.type "
    "FROM conversion_action"))
print("\nAds 转化动作全表:")
for r in rows:
    ca = r.conversion_action
    print(f"  [{ca.status.name[:8]:<8}] {ca.name[:40]:<40} "
          f"cat={ca.category.name:<22} type={ca.type.name:<26} "
          f"primary={ca.primary_for_goal}")
