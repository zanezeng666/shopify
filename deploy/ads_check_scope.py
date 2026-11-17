# -*- coding: utf-8 -*-
"""验证 PMax 系列商品定向（listing_scope）是否锁定医疗 collection。"""
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


def try_q(label, q):
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"  ✓ {label}")
        return rs
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ {label}: {str(e)[:100]}")
        return None


print("=== PMax 系列商品定向 ===")
# listing_scope（collection 定向）
ls = try_q("listing_scope 查询",
           "SELECT listing_scope.resource_name, listing_scope.listing_scope "
           "FROM listing_scope "
           f"WHERE campaign.id = {PMAX}")
if ls is not None:
    if not ls:
        print("  ⚠ 无 listing_scope（系列=全目录投放！）")
    for r in ls:
        for sc in r.listing_scope.listing_scope:
            dim = sc.dimension_value
            if hasattr(dim, "id"):
                print(f"  定向: collection_id={dim.id}")
            else:
                print(f"  定向: {str(dim)[:80]}")

# shopping_setting（MC 关联+国家）
ss = try_q("shopping_setting 查询",
           "SELECT campaign.shopping_setting.merchant_center_id, "
           "campaign.shopping_setting.sales_country, "
           "campaign.shopping_setting.feed_label, "
           "campaign.status, campaign.name "
           "FROM campaign "
           f"WHERE campaign.id = {PMAX}")
for r in (ss or []):
    s = r.campaign.shopping_setting
    print(f"  MC={s.merchant_center_id} 国家={s.sales_country} "
          f"feed={s.feed_label} 状态={r.campaign.status.name}")

# 资产组的 listing_group（树根维度）
aglg = try_q("资产组 listing_group 根",
             "SELECT asset_group_listing_group_filter.resource_name, "
             "asset_group_listing_group_filter.hierarchy, "
             "asset_group_listing_group_filter.listing_source, "
             "asset_group.id "
             "FROM asset_group_listing_group_filter "
             f"WHERE campaign.id = {PMAX}")
for r in (aglg or []):
    print(f"  资产组[{r.asset_group.id}] filter="
          f"{r.asset_group_listing_group_filter.resource_name.split('/')[-1][:40]}"
          f" source={r.asset_group_listing_group_filter.listing_source.name}")
