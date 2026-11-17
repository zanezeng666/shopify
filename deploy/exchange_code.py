# -*- coding: utf-8 -*-
"""用回调 code 换取新 refresh token（双 scope: adwords+content）"""
import os
import sys
import tempfile
import httpx

CODE = ("4/0AUn6Hd_tp0heG80GA_ffcZes5G4ZpGY_EZP4xoNLxu8k4"
        "Ubtj86FM-sZfJ-T3rTn1Holtw")
REDIRECT = "http://localhost:8745/callback"

cid = csec = None
for p in (os.path.join(tempfile.gettempdir(), "bmai_env.txt"),
          r"C:\Users\admin\AppData\Local\Temp\bmai_env.txt"):
    if os.path.exists(p):
        kv = {}
        for line in open(p, encoding="utf-8-sig", errors="ignore"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                kv[k.strip()] = v.strip()
        cid, csec = kv.get("GOOGLE_CLIENT_ID"), kv.get("GOOGLE_CLIENT_SECRET")
        if cid and csec:
            break
if not (cid and csec):
    sys.exit("credentials not found")

r = httpx.post("https://oauth2.googleapis.com/token", data={
    "code": CODE, "client_id": cid, "client_secret": csec,
    "redirect_uri": REDIRECT, "grant_type": "authorization_code"}, timeout=30)
d = r.json()
if "refresh_token" not in d:
    sys.exit(f"FAIL: {r.status_code} {d}")
rt = d["refresh_token"]
out = os.path.join(tempfile.gettempdir(), "new_refresh.txt")
with open(out, "w") as f:
    f.write(rt)
print("scope:", d.get("scope"))
print("refresh_token saved:", out, f"({rt[:8]}...{rt[-4:]})")

# 立即用新 refresh token 实测 Content API
tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": cid, "client_secret": csec, "refresh_token": rt,
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
r2 = httpx.get(
    f"https://shoppingcontent.googleapis.com/content/v2.1/136469408/products?maxResults=5",
    headers={"Authorization": f"Bearer {tok}"}, timeout=60)
print("Content API test:", r2.status_code)
if r2.status_code == 200:
    j = r2.json()
    print("  products sample:", len(j.get("resources", [])),
          "| kind:", j.get("kind"))
