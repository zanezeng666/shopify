# -*- coding: utf-8 -*-
"""PMax listing_group_filter 字段探测 + 商品组树。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

BASE = "FROM asset_group_listing_group_filter WHERE campaign.id = "
TRY = [
    # 逐步精简直到成功
    "SELECT asset_group_listing_group_filter.resource_name, "
    "asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.case_value.product_type.value, "
    "asset_group_listing_group_filter.case_value.product_item_id.value, "
    "asset_group_listing_group_filter.case_value.product_brand.value ",
    "SELECT asset_group_listing_group_filter.resource_name, "
    "asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.case_value.product_type.value ",
    "SELECT asset_group_listing_group_filter.resource_name, "
    "asset_group_listing_group_filter.id ",
]
for q in TRY:
    try:
        rs = list(gas.search(customer_id=CID, query=q + BASE + str(PMAX)))
        print(f"OK rows={len(rs)}")
        if not rs:
            print("  (空 = 无商品组划分 = ALL_PRODUCTS 全商品)")
        for r in rs:
            f = r.asset_group_listing_group_filter
            cv = f.case_value
            print(f"  id={f.id} ptype={cv.product_type.value or '-'} "
                  f"brand={cv.product_brand.value or '-'} "
                  f"item={cv.product_item_id.value or '-'}")
        break
    except Exception as e:  # noqa
        msg = str(e)
        hint = [ln for ln in msg.split("\n") if "Unrecognized" in ln]
        print(f"FAIL {hint[:1]}")

print("\n=== shopping_performance_view：PMax 实际投放商品类别（近30天）===")
try:
    q = (
        "SELECT shopping_performance_view.category5, "
        "metrics.clicks, metrics.impressions, metrics.cost_micros, "
        "metrics.conversions "
        f"FROM shopping_performance_view WHERE campaign.id = {PMAX} "
        "AND metrics.impressions > 0"
    )
    rs = list(gas.search(customer_id=CID, query=q))
    for r in rs:
        v = r.shopping_performance_view
        print(f"  {str(v.category5)[:40]:40} "
              f"imp={r.metrics.impressions} clk={r.metrics.clicks} "
              f"cost=¥{r.metrics.cost_micros/1e6:.0f} "
              f"conv={r.metrics.conversions:.0f}")
except Exception as e:  # noqa
    msg = str(e)
    hint = [ln for ln in msg.split("\n") if ("Unrecognized" in ln
                                             or "error" in ln.lower())]
    print(f"  查询失败: {hint[:2]}")
