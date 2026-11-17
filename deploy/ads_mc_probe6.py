# -*- coding: utf-8 -*-
"""product_link 字段名变体最后一轮 + 元数据字典查 product_link 可选字段。"""
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

# proto 反射 ProductLink 消息字段
print("=== ProductLink proto 字段 ===")
from google.ads.googleads.v26.resources.types import product_link as pl_mod  # noqa: E402

for fname in pl_mod.ProductLink.meta.fields:
    print(f"  {fname}")

print("\n=== GAQL 变体 ===")
for q in (
    "SELECT product_link.product_link_id FROM product_link",
    "SELECT product_link.product_link_id, "
    "product_link.merchant_center_link.merchant_center_id "
    "FROM product_link",
):
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"OK rows={len(rs)}")
        for r in rs[:8]:
            pl = r.product_link
            print(f"  link_id={pl.product_link_id} type={pl.type_.name} "
                  f"MC={pl.merchant_center.merchant_center_id} "
                  f"dump={pl}")
        break
    except Exception as e:  # noqa
        errs = [ln.strip() for ln in str(e).split("\n")
                if "Unrecognized" in ln or "message:" in ln.lower()]
        print(f"FAIL {errs[:1]}")
