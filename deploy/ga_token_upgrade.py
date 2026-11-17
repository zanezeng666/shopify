# -*- coding: utf-8 -*-
"""OAuth code 换新 refresh token（含 analytics.edit）→ 写回 .env →
GA4 标 generate_lead 为 key event → readback 确认。"""
import os

import httpx
from dotenv import load_dotenv

ENV_PATH = "/home/jason/shopify-admin/.env"
CODE = ("4/0AUn6Hd8GT51PKQDlz3eX97pUhrUR4Wj3yWifuiv-1nynNciKUei"
        "2cCEkbuKUafAj7vDC7Q")
PROPERTY = "313397200"

load_dotenv(ENV_PATH)
cid, csc = os.environ["GOOGLE_CLIENT_ID"], os.environ["GOOGLE_CLIENT_SECRET"]

# 1) code -> tokens
r = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": cid, "client_secret": csc, "code": CODE,
    "grant_type": "authorization_code",
    "redirect_uri": "http://localhost:1"}, timeout=30)
print("token exchange:", r.status_code)
toks = r.json()
if "refresh_token" not in toks:
    print("FAIL:", toks); raise SystemExit(1)
print("granted scopes:")
for s in toks["scope"].split():
    print(" -", s)
assert "analytics.edit" in toks["scope"], "analytics.edit 未授予!"
new_rt = toks["refresh_token"]

# 2) 备份 .env 并替换 refresh token
with open(ENV_PATH, encoding="utf-8") as f:
    lines = f.readlines()
os.makedirs(os.path.dirname(ENV_PATH), exist_ok=True)
with open(ENV_PATH + ".bak_oauth_20261115", "w", encoding="utf-8") as f:
    f.writelines(lines)
out = []
for ln in lines:
    if ln.startswith("GOOGLE_REFRESH_TOKEN="):
        out.append(f"GOOGLE_REFRESH_TOKEN={new_rt}\n")
    else:
        out.append(ln)
with open(ENV_PATH, "w", encoding="utf-8") as f:
    f.writelines(out)
print(".env updated (backup: .env.bak_oauth_20261115)")

# 3) 新 refresh token 换 access token
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": cid, "client_secret": csc, "refresh_token": new_rt,
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}

# 4) 现有 key events
ke = httpx.get(
    f"https://analyticsadmin.googleapis.com/v1alpha/properties/{PROPERTY}/keyEvents",
    headers=H, timeout=30).json()
print("\n现有 key events:")
names = [i["eventName"] for i in ke.get("keyEvents", [])]
for n in names:
    print(" -", n)

# 5) 标 generate_lead
if "generate_lead" in names:
    print("generate_lead 已是 key event，跳过")
else:
    r2 = httpx.post(
        f"https://analyticsadmin.googleapis.com/v1alpha/properties/{PROPERTY}/keyEvents",
        headers=H, json={"eventName": "generate_lead"}, timeout=30)
    print("\n标记 generate_lead:", r2.status_code, r2.text[:200])

# 6) readback
ke2 = httpx.get(
    f"https://analyticsadmin.googleapis.com/v1alpha/properties/{PROPERTY}/keyEvents",
    headers=H, timeout=30).json()
print("\n最终 key events:", [i["eventName"] for i in ke2.get("keyEvents", [])])
