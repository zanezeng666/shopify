# -*- coding: utf-8 -*-
"""长尾型号词竞价合理性查证：ELIGIBLE词门槛 + 真实搜索词分布 + PMax搜索词对照"""
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
D1, D2 = "2026-09-14", "2026-11-13"

print("=== ① Medical: ELIGIBLE 词的竞价门槛（首页/页顶 CPC 估算） ===")
try:
    q1 = ("SELECT ad_group_criterion.keyword.text, "
          "ad_group_criterion.cpc_bid_micros, "
          "ad_group_criterion.position_estimates.first_page_cpc_micros, "
          "ad_group_criterion.position_estimates.top_of_page_cpc_micros, "
          "ad_group_criterion.quality_info.quality_score "
          "FROM ad_group_criterion WHERE campaign.id = 24448362668 "
          "AND ad_group_criterion.type = 'KEYWORD' "
          "AND ad_group_criterion.system_serving_status = 'ELIGIBLE'")
    rows = list(gac.search(customer_id=CID, query=q1))
    shown_gate = [r for r in rows
                  if r.ad_group_criterion.position_estimates.first_page_cpc_micros > 0]
    print(f"  ELIGIBLE 总数={len(rows)}，其中有首页出价估算（=有真实搜索发生）={len(shown_gate)}")
    for r in sorted(shown_gate, key=lambda r: -r.ad_group_criterion.position_estimates.first_page_cpc_micros)[:15]:
        k = r.ad_group_criterion
        fp = k.position_estimates.first_page_cpc_micros / 1e6
        tp = k.position_estimates.top_of_page_cpc_micros / 1e6
        qs = k.quality_info.quality_score
        print(f"  {k.keyword.text[:34]:34s} 首页门槛=¥{fp:6.2f} 页顶=¥{tp:6.2f} "
              f"质量分={qs if qs else '-'}")
except Exception as e:
    print(f"  [失败: {str(e)[:150]}]")

print("\n=== ② Search 渠道 60 天真实发生的搜索词（全账户） ===")
try:
    q2 = ("SELECT search_term_view.search_term, metrics.impressions, "
          "metrics.clicks, metrics.cost_micros "
          "FROM search_term_view "
          f"WHERE segments.date BETWEEN '{D1}' AND '{D2}'")
    rows = list(gac.search(customer_id=CID, query=q2))
    print(f"  60 天搜索词总数={len(rows)}（Search 渠道）")
    for r in sorted(rows, key=lambda r: -r.metrics.impressions)[:15]:
        m = r.metrics
        print(f"  {r.search_term_view.search_term[:44]:44s} imp={m.impressions:4d} "
              f"clk={m.clicks:3d} cost=¥{m.cost_micros/1e6:.2f}")
except Exception as e:
    print(f"  [失败: {str(e)[:150]}]")

print("\n=== ③ PMax 60 天捕获的搜索词 Top30（按点击）===")
try:
    q3 = ("SELECT campaign_search_term_view.search_term, metrics.impressions, "
          "metrics.clicks, metrics.cost_micros, metrics.conversions "
          "FROM campaign_search_term_view "
          f"WHERE segments.date BETWEEN '{D1}' AND '{D2}' "
          "AND campaign.id = 24441391608")
    rows = list(gac.search(customer_id=CID, query=q3))
    tot_c = sum(r.metrics.clicks for r in rows)
    print(f"  PMax 搜索词总数={len(rows)}，合计点击={tot_c}")
    for r in sorted(rows, key=lambda r: -r.metrics.clicks)[:30]:
        m = r.metrics
        print(f"  {r.campaign_search_term_view.search_term[:46]:46s} imp={m.impressions:5d} "
              f"clk={m.clicks:3d} conv={m.conversions:3.0f} cost=¥{m.cost_micros/1e6:7.2f}")
except Exception as e:
    print(f"  [失败: {str(e)[:150]}]")
