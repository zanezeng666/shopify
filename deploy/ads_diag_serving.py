# -*- coding: utf-8 -*-
"""诊断 Search 0 展示根因（只读）。"""
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


def q(label, query, fmt):
    print(f"=== {label} ===")
    try:
        for r in list(gas.search(customer_id=CID, query=query)):
            print(fmt(r))
    except Exception as e:  # noqa: BLE001
        print("查询失败:", str(e)[:200])
    print()


q("全账户系列状态与累计花费",
  "SELECT campaign.id, campaign.name, campaign.status, "
  "campaign.serving_status, metrics.impressions, metrics.clicks, "
  "metrics.cost_micros FROM campaign ORDER BY campaign.id",
  lambda r: (f"{r.campaign.name} | {r.campaign.status.name} | "
             f"serving={r.campaign.serving_status.name} | "
             f"展示={r.metrics.impressions} 点击={r.metrics.clicks} "
             f"花费=¥{r.metrics.cost_micros/1e6:.2f}"))

q("Search 广告组状态",
  "SELECT ad_group.name, ad_group.status FROM ad_group "
  "WHERE campaign.id = 24448362668 LIMIT 12",
  lambda r: f"{r.ad_group.name} | {r.ad_group.status.name}")

q("Search 广告(文字广告)与政策审批",
  "SELECT ad_group_ad.status, ad_group_ad.policy_summary.approval_status, "
  "ad_group_ad.ad.type FROM ad_group_ad WHERE campaign.id = 24448362668",
  lambda r: (f"ad.status={r.ad_group_ad.status.name} | "
         f"审批={r.ad_group_ad.policy_summary.approval_status.name} | "
         f"类型={r.ad_group_ad.ad.type_.name if r.ad_group_ad.ad.type_ else '?'}"))

q("Search 关键词投放状态抽样",
  "SELECT ad_group_criterion.keyword.text, ad_group_criterion.status, "
  "ad_group_criterion.system_serving_status "
  "FROM ad_group_criterion "
  "WHERE campaign.id = 24448362668 AND ad_group_criterion.type = 'KEYWORD' "
  "LIMIT 8",
  lambda r: (f"{r.ad_group_criterion.keyword.text:32s} | "
             f"{r.ad_group_criterion.status.name} | "
             f"{r.ad_group_criterion.system_serving_status.name}"))
