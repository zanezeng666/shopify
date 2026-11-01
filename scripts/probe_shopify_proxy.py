# -*- coding: utf-8 -*-
"""经 127.0.0.1:7897 代理探活店铺凭据（shop.json）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx
from sqlalchemy import text

from shopify_admin.core.database import get_engine

PROXY = "http://127.0.0.1:7897"

with get_engine().connect() as c:
    row = c.execute(text("SELECT api_key, api_secret, domain FROM stores WHERE id=1")).fetchone()
key, secret, domain = row
print(f"domain={domain} key_len={len(key)} secret_set={bool(secret)}")

base = f"https://{domain}.myshopify.com/admin/api/2024-10/"
with httpx.Client(base_url=base, proxy=PROXY, timeout=30) as cl:
    if secret:
        auth = httpx.BasicAuth(key, secret)
        hdrs = {}
    else:
        auth = None
        hdrs = {"X-Shopify-Access-Token": key}
    r = cl.get("shop.json", auth=auth, headers=hdrs)
    print("status:", r.status_code)
    if r.status_code == 200:
        shop = r.json().get("shop", {})
        print("shop:", shop.get("name"), shop.get("myshopify_domain"), shop.get("primary_location_id"))
    else:
        print(r.text[:300])
