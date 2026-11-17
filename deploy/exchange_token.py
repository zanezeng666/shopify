# -*- coding: utf-8 -*-
"""用授权码换 refresh_token 并存 .env。"""
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

CODE = ("4/0AUn6Hd_nraVngmpS42visHA-uHex9g6WoqRDJdPLKmultW5z"
        "GxwmVU9ojczj8lnrK5WRNQ")
r = httpx.post("https://oauth2.googleapis.com/token", data={
    "code": CODE,
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
    "grant_type": "authorization_code"}, timeout=30)
d = r.json()
if "refresh_token" not in d:
    print("失败:", r.status_code, d)
    sys.exit(1)

rt = d["refresh_token"]
env_path = "/home/jason/shopify-admin/.env"
with open(env_path) as f:
    env = f.read()
if "GOOGLE_REFRESH_TOKEN=" in env:
    import re
    env = re.sub(r"GOOGLE_REFRESH_TOKEN=.*",
                 f"GOOGLE_REFRESH_TOKEN={rt}", env)
else:
    env += f"\nGOOGLE_REFRESH_TOKEN={rt}\n"
with open(env_path, "w") as f:
    f.write(env)
os.chmod(env_path, 0o600)

ti = httpx.get("https://oauth2.googleapis.com/tokeninfo", params={
    "access_token": d["access_token"]}, timeout=15).json()
print("refresh_token 已存 .env (前12位:", rt[:12] + "...)")
print("access_token 有效性:", ti.get("scope", ti))
print("expires_in(s):", ti.get("expires_in"))
