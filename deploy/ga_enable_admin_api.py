# -*- coding: utf-8 -*-
"""尝试经 Service Usage API 启用 Analytics Admin API，成功则直接标 key event。"""
import time

import httpx
from dotenv import load_dotenv
import os

ENV_PATH = "/home/jason/shopify-admin/.env"
PROPERTY = "313397200"
load_dotenv(ENV_PATH)

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}

r = httpx.post(
    "https://serviceusage.googleapis.com/v1/projects/415310719420"
    "/services/analyticsadmin.googleapis.com:enable",
    headers=H, timeout=60)
print("enable:", r.status_code, r.text[:300])
if r.status_code >= 400:
    raise SystemExit("需要手动启用（点链接）")

for _ in range(6):
    time.sleep(5)
    g = httpx.get(
        f"https://analyticsadmin.googleapis.com/v1alpha/properties/{PROPERTY}/keyEvents",
        headers=H, timeout=30)
    if g.status_code == 200:
        break
print("keyEvents GET:", g.status_code)
names = [i["eventName"] for i in g.json().get("keyEvents", [])]
print("现有:", names or "(空)")
if "generate_lead" not in names:
    p = httpx.post(
        f"https://analyticsadmin.googleapis.com/v1alpha/properties/{PROPERTY}/keyEvents",
        headers=H, json={"eventName": "generate_lead"}, timeout=30)
    print("标记 generate_lead:", p.status_code, p.text[:200])
g2 = httpx.get(
    f"https://analyticsadmin.googleapis.com/v1alpha/properties/{PROPERTY}/keyEvents",
    headers=H, timeout=30)
print("最终:", [i["eventName"] for i in g2.json().get("keyEvents", [])])
