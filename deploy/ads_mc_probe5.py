# -*- coding: utf-8 -*-
"""product_link 资源探 MC ID + 系列数据视图兜底。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

QS = [
    "SELECT product_link.id, "
    "product_link.merchant_center_link.merchant_center_id "
    "FROM product_link",
    "SELECT product_link.resource_name, product_link.id FROM product_link",
    "SELECT shopping_performance_view.product_item_id "
    "FROM shopping_performance_view LIMIT 1",
]
found = None
for q in QS:
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"OK {q.split('FROM')[1].strip()[:30]} rows={len(rs)}")
        for r in rs[:6]:
            pl = getattr(r, "product_link", None)
            if pl is not None:
                mc = pl.merchant_center_link.merchant_center_id
                print(f"  product_link id={pl.id} MC={mc}")
                found = found or mc
        if found:
            break
    except Exception as e:  # noqa
        errs = [ln.strip() for ln in str(e).split("\n")
                if "Unrecognized" in ln or "message:" in ln.lower()]
        print(f"FAIL {errs[:1] or str(e)[:120]}")

if not found:
    raise SystemExit("product_link 也没拿到 MC ID")
print(f"\nMC ID = {found}")
