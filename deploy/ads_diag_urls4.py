# -*- coding: utf-8 -*-
"""诊断 v6：Search 9 广告 final_urls 明细 + 全账号 URL 类资产政策审计。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
SEARCH = 24448362668
BAD = {"DISAPPROVED", "AREA_OF_INTEREST_ONLY", "CERTIFICATE_REQUIRED",
       "LIMITED"}

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
rows = lambda q: list(gas.search(customer_id=CID, query=q))  # noqa

print("=== Search 广告 final_urls ===")
for r in rows(
    "SELECT ad_group_ad.ad.final_urls, ad_group_ad.status, "
    "ad_group.name FROM ad_group_ad WHERE campaign.id = "
    f"{SEARCH} AND ad_group_ad.status != 'REMOVED'"
):
    a = r.ad_group_ad
    print(f"  [{a.status.name}] {r.ad_group.name[:28]:28} {a.ad.final_urls}")

print("\n=== 全账号 sitelink/page_feed/call 类资产政策 ===")
n = 0
for r in rows(
    "SELECT asset.resource_name, asset.name, asset.type, "
    "asset.policy_summary.approval_status, "
    "asset.policy_summary.policy_topic_entries "
    "FROM asset WHERE asset.type IN ('SITELINK', 'PAGE_FEED', 'CALL', "
    "'PROMOTION')"
):
    a = r.asset
    n += 1
    st = (a.policy_summary.approval_status.name
          if a.policy_summary else "-")
    ents = "; ".join(
        f"{e.type_}/{e.entry_type.name}" for e in
        (a.policy_summary.policy_topic_entries or [])) if a.policy_summary else ""
    mark = "  ◀◀" if st in BAD else ""
    print(f"  {a.type.name:12} pol={st:16} "
          f"{a.name[:40]:40}{mark} {ents[:70]}")
print(f"  共 {n} 个 URL 类资产")

print("\n=== 全账号挂链情况（sitelink 挂在哪些系列，含 REMOVED）===")
for tbl in ("campaign_asset", "asset_group_asset"):
    try:
        for r in rows(
            f"SELECT campaign.id, campaign.name, campaign.status, "
            f"{tbl}.asset, {tbl}.status FROM {tbl}"
        ):
            t = getattr(r, tbl)
            if "assets/4" in t.asset:  # 全量太多，只看非当前系列的引用计数由下步统计
                pass
    except Exception as e:  # noqa
        print(f"  {tbl} 全量查询失败: {type(e).__name__}")
        continue
print("(明细见上)")
