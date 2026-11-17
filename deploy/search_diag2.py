# -*- coding: utf-8 -*-
"""Search 零流量根因：系列状态分布 + 出价策略 + 关键词首页出价门槛"""
import os

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")

from google.ads.googleads.client import GoogleAdsClient

ads = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "login_customer_id": CID,
    "use_proto_plus": True,
})
gac = ads.get_service("GoogleAdsService")

print("=== ① Search 系列 status 分布 + 预算 + 出价策略（ENABLED 的） ===")
q = ("SELECT campaign.id, campaign.name, campaign.status, "
     "campaign.bidding_strategy_type, campaign_budget.amount_micros "
     "FROM campaign WHERE campaign.advertising_channel_type = 'SEARCH'")
stat = {}
for row in gac.search(customer_id=CID, query=q):
    c = row.campaign
    stat[c.status.name] = stat.get(c.status.name, 0) + 1
    if c.status.name == "ENABLED":
        print(f"  [{c.id}] {c.name[:36]:36s} 预算=¥{row.campaign_budget.amount_micros/1e6:6.0f}/天 "
              f"出价={c.bidding_strategy_type.name}")
print(f"  状态分布: {stat}")

print("\n=== ② Medical Search 关键词出价 vs 首页/页顶门槛 ===")
q2 = ("SELECT ad_group_criterion.keyword.text, "
      "ad_group_criterion.status, "
      "ad_group_criterion.cpc_bid_micros, "
      "ad_group_criterion.position_estimates.first_page_cpc_micros, "
      "ad_group_criterion.position_estimates.top_of_page_cpc_micros, "
      "ad_group_criterion.quality_info.quality_score "
      "FROM ad_group_criterion WHERE campaign.id = 24448362668 "
      "AND ad_group_criterion.type = 'KEYWORD' LIMIT 40")
for row in gac.search(customer_id=CID, query=q2):
    k = row.ad_group_criterion
    fp = k.position_estimates.first_page_cpc_micros / 1e6
    tp = k.position_estimates.top_of_page_cpc_micros / 1e6
    bid = k.cpc_bid_micros / 1e6
    qs = k.quality_info.quality_score
    qs_s = f"{qs}" if qs else "无(零展示)"
    print(f"  {k.keyword.text[:30]:30s} 出价=¥{bid:5.2f} 首页门槛=¥{fp:6.2f} "
          f"页顶=¥{tp:6.2f} 质量分={qs_s} 状态={k.status.name}")

print("\n=== ③ Medical Search 广告状态（是否有获批广告在投） ===")
q3 = ("SELECT ad_group_ad.status, ad_group_ad.policy_summary.approval_status, "
      "ad_group_ad.ad.type, metrics.impressions "
      "FROM ad_group_ad WHERE campaign.id = 24448362668 "
      "AND segments.date BETWEEN '2026-10-30' AND '2026-11-13'")
try:
    for row in gac.search(customer_id=CID, query=q3):
        a = row.ad_group_ad
        print(f"  状态={a.status.name} 审核={a.policy_summary.approval_status.name} "
              f"类型={a.ad.type_.name} imp={row.metrics.impressions}")
except Exception as e:
    print(f"  [查询失败: {str(e)[:120]}]")
