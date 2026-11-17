# -*- coding: utf-8 -*-
"""反射 proto 拿字段名 + 重查现有 listing 树 + Search RSA 文本。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads import v26

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608
SEARCH = 24448362668

print("=== A) AssetGroupListingGroupFilter proto 字段 ===")
from google.ads.googleads.v26.resources.types.asset_group_listing_group_filter \
    import AssetGroupListingGroupFilter as AGLGF

for f in AGLGF.meta.fields.values():
    print(f"  {f.name:32} {f.number}")

print("\n=== B) ListingGroupFilterDimension proto ===")
try:
    from google.ads.googleads.v26.common.types.listing_group_info \
        import ListingGroupFilterDimension as Dim
except ImportError:
    try:
        from google.ads.googleads.v26.common.types.asset_group_data \
            import ListingGroupFilterDimension as Dim
    except ImportError:
        Dim = None
        print("  (两路径均无，跳过；case_value 已知可用 product_type.value)")
if Dim:
    for f in Dim.meta.fields.values():
        print(f"  {f.name}")

print("\n=== C) RSA proto（Search 文本路径）===")
from google.ads.googleads.v26.common.types.ad_type_infos \
    import ResponsiveSearchAdInfo as RSA

for f in RSA.meta.fields.values():
    print(f"  {f.name}")

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

print("\n=== D) 现有 listing 树（全字段）===")
q = (
    "SELECT asset_group_listing_group_filter.resource_name, "
    "asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.asset_group, "
    "asset_group_listing_group_filter.parent_listing_group_filter, "
    "asset_group_listing_group_filter.path, "
    "asset_group_listing_group_filter.case_value.product_type.value "
    f"FROM asset_group_listing_group_filter WHERE campaign.id = {PMAX}"
)
try:
    for r in gas.search(customer_id=CID, query=q):
        f = r.asset_group_listing_group_filter
        print(f"  id={f.id} parent={f.parent_listing_group_filter or '-'} "
              f"ptype={f.case_value.product_type.value or '-'} "
              f"rn={f.resource_name}")
except Exception as e:  # noqa
    print(f"  失败: {str(e)[:400]}")

print("\n=== E) Search RSA 文本（asset 表按 ad_group_ad 关联不行，改探字段）===")
try:
    q2 = (
        "SELECT ad_group_ad.ad.id, ad_group_ad.ad.name, "
        "ad_group_ad.ad.responsive_search_ad.headlines "
        f"FROM ad_group_ad WHERE campaign.id = {SEARCH}")
    n = 0
    for r in gas.search(customer_id=CID, query=q2):
        ad = r.ad_group_ad.ad
        hls = (ad.responsive_search_ad.headlines or [])
        print(f"  ad={ad.id} {ad.name[:20]!r} headlines={len(hls)}")
        for h in hls[:5]:
            print(f"    H: {h.text!r}")
        n += 1
    print(f"  共 {n} 个广告")
except Exception as e:  # noqa
    print(f"  失败: {str(e)[:300]}")
