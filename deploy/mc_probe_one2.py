# -*- coding: utf-8 -*-
"""看 productAttributes 键+两类 offer 样本的内容（title/link/types/来源）。"""
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MC = "136469408"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
HDR = {"Authorization": f"Bearer {at}"}

seen = {"shopify": 0, "other": 0}
tok = None
shown_keys = False
for page in range(4):
    params = {"pageSize": 250}
    if tok:
        params["pageToken"] = tok
    r = httpx.get(
        f"https://merchantapi.googleapis.com/products/v1/accounts/{MC}"
        f"/products", params=params, headers=HDR, timeout=60)
    b = r.json()
    for p in b.get("products", []):
        o = p.get("offerId", "")
        kind = "shopify" if o.startswith("shopify_") else "other"
        if seen[kind] < 3:
            seen[kind] += 1
            print("=" * 64)
            print(f"[{kind}] offer={o[:60]}")
            print(f"  dataSource={p.get('dataSource', '')[-40:]} "
                  f"archived={p.get('archived')} "
                  f"version={p.get('versionNumber')}")
            pa = p.get("productAttributes", {})
            if not shown_keys:
                print(f"  productAttributes 键: {sorted(pa.keys())}")
                shown_keys = True
            for k in ("title", "link", "productTypes", "itemGroupId",
                      "identifierExists", "mpn", "brand"):
                if k in pa:
                    print(f"  {k} = {str(pa[k])[:76]}")
    tok = b.get("nextPageToken")
    if not tok:
        break
