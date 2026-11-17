# -*- coding: utf-8 -*-
"""侦察3c: 多版本容错探 shopping_setting(v25 不可查)。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}",
     "Content-Type": "application/json", "developer-token": "unused"}
CID = "7059800494"

q = ("SELECT campaign.id, campaign.name, "
     "campaign.shopping_setting.merchant_center_id, "
     "campaign.shopping_setting.feed_label, "
     "campaign.shopping_setting.sales_country "
     "FROM campaign WHERE campaign.advertising_channel_type = "
     "'PERFORMANCE_MAX'")
for ver in ("v22", "v20", "v18", "v17", "v16"):
    try:
        r = httpx.post(
            f"https://googleads.googleapis.com/{ver}/customers/{CID}/"
            "googleAds:searchStream", headers=H, json={"query": q},
            timeout=30)
        if r.status_code != 200:
            print(f"[{ver}] HTTP {r.status_code} {r.text[:80]}")
            continue
        rows = r.json() if isinstance(r.json(), list) else [r.json()]
    except Exception as e:
        print(f"[{ver}] {type(e).__name__}: {str(e)[:90]}")
        continue
    n = 0
    for b in rows:
        for e in b.get("results", []):
            c = e["campaign"]
            ss = c.get("shoppingSetting", {})
            n += 1
            print(f"[{ver}] {c['id']} {c['name'][:26]:<26} "
                  f"MC={ss.get('merchantCenterId')} "
                  f"国={ss.get('salesCountry')} feed={ss.get('feedLabel')}")
        if "error" in b:
            print(f"[{ver}] ERR:",
                  b["error"]["details"][0]["errors"][0]["message"][:110])
    if n:
        break
