# -*- coding: utf-8 -*-
"""Analytics Admin API 已启用：标 generate_lead 为 key event + readback。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
PROPERTY = "313397200"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
URL = (f"https://analyticsadmin.googleapis.com/v1alpha/properties/{PROPERTY}"
       "/keyEvents")

g = httpx.get(URL, headers=H, timeout=30)
print("keyEvents GET:", g.status_code)
names = [i["eventName"] for i in g.json().get("keyEvents", [])]
print("现有:", names or "(空)")

if "generate_lead" not in names:
    p = httpx.post(URL, headers=H, json={"eventName": "generate_lead"},
                   timeout=30)
    print("标记 generate_lead:", p.status_code, p.text[:150])

g2 = httpx.get(URL, headers=H, timeout=30)
final = [(i["eventName"], i.get("countingMethod"), i.get("defaultValue"))
         for i in g2.json().get("keyEvents", [])]
print("最终:", final)
