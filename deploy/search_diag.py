# -*- coding: utf-8 -*-
"""Search 系列点击流量诊断：消耗/点击/IS 丢失归因/关键词明细"""
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
D1, D2 = "2026-10-30", "2026-11-13"

print("=== ① 38+1 Search 系列 14 天汇总（按消耗降序，前 15 + 全量合计） ===")
base = ("SELECT campaign.id, campaign.name, campaign.status, "
        "metrics.impressions, metrics.clicks, metrics.ctr, "
        "metrics.average_cpc, metrics.cost_micros, "
        "campaign_budget.amount_micros "
        f"FROM campaign WHERE segments.date BETWEEN '{D1}' AND '{D2}' "
        "AND campaign.advertising_channel_type = 'SEARCH'")
try:
    qis = base.replace("campaign_budget.amount_micros",
                       "campaign_budget.amount_micros, "
                       "metrics.search_impression_share, "
                       "metrics.search_budget_lost_impression_share, "
                       "metrics.search_rank_lost_impression_share")
    rows = list(gac.search(customer_id=CID, query=qis))
    has_is = True
except Exception as e:
    rows = list(gac.search(customer_id=CID, query=base))
    has_is = False
    print(f"  [IS 字段不可用: {str(e)[:80]}]")

rows.sort(key=lambda r: r.metrics.cost_micros, reverse=True)
tot = dict(imp=0, clk=0, cost=0)
for i, row in enumerate(rows):
    m, c = row.metrics, row.campaign
    tot["imp"] += m.impressions; tot["clk"] += m.clicks; tot["cost"] += m.cost_micros
    if i < 15:
        line = (f"  {c.name[:34]:34s} ¥{m.cost_micros/1e6:8.1f} "
                f"imp={m.impressions:6d} clk={m.clicks:4d} "
                f"ctr={m.ctr:.2f}% cpc=¥{m.average_cpc/1e6:.2f}")
        if has_is:
            line += (f" IS={m.search_impression_share:.0%} "
                     f"丢预算={m.search_budget_lost_impression_share:.0%} "
                     f"丢排名={m.search_rank_lost_impression_share:.0%}")
        print(line)
print(f"  ---- 合计 {len(rows)} 个系列: imp={tot['imp']} clk={tot['clk']} "
      f"cost=¥{tot['cost']/1e6:.1f} ctr={tot['clk']/max(tot['imp'],1):.2%} "
      f"日均点击={tot['clk']/14:.1f}")

print("\n=== ② 全 Search 日粒度趋势（近 14 天） ===")
q2 = (f"SELECT segments.date, metrics.impressions, metrics.clicks, "
      f"metrics.cost_micros FROM campaign "
      f"WHERE segments.date BETWEEN '{D1}' AND '{D2}' "
      "AND campaign.advertising_channel_type = 'SEARCH'")
daily = {}
for row in gac.search(customer_id=CID, query=q2):
    d = row.segments.date
    a = daily.setdefault(d, [0, 0, 0])
    a[0] += row.metrics.impressions; a[1] += row.metrics.clicks
    a[2] += row.metrics.cost_micros
for d in sorted(daily):
    imp, clk, cost = daily[d]
    print(f"  {d}: imp={imp:6d} clk={clk:4d} cost=¥{cost/1e6:7.1f}")

med = next((r.campaign for r in rows if "Medical" in r.campaign.name), None)
if med:
    print(f"\n=== ③ Medical Search ({med.name} id={med.id}) 关键词明细 Top12 ===")
    q3 = ("SELECT ad_group_criterion.keyword.text, "
          "ad_group_criterion.keyword.match_type, "
          "metrics.impressions, metrics.clicks, metrics.ctr, "
          "metrics.average_cpc, metrics.cost_micros "
          f"FROM keyword_view WHERE campaign.id = {med.id} "
          f"AND segments.date BETWEEN '{D1}' AND '{D2}'")
    kws = list(gac.search(customer_id=CID, query=q3))
    kws.sort(key=lambda r: r.metrics.cost_micros, reverse=True)
    for row in kws[:12]:
        m, k = row.metrics, row.ad_group_criterion.keyword
        print(f"  [{k.match_type.name[:7]:7s}] {k.text[:32]:32s} "
              f"imp={m.impressions:5d} clk={m.clicks:3d} "
              f"cpc=¥{m.average_cpc/1e6:.2f} cost=¥{m.cost_micros/1e6:.1f}")

    print(f"\n=== ④ Medical Search 搜索词报告 Top12 ===")
    q4 = ("SELECT search_term_view.search_term, metrics.impressions, "
          "metrics.clicks, metrics.cost_micros "
          f"FROM search_term_view WHERE campaign.id = {med.id} "
          f"AND segments.date BETWEEN '{D1}' AND '{D2}'")
    try:
        sts = list(gac.search(customer_id=CID, query=q4))
        sts.sort(key=lambda r: r.metrics.cost_micros, reverse=True)
        for row in sts[:12]:
            m = row.metrics
            print(f"  {row.search_term_view.search_term[:40]:40s} "
                  f"imp={m.impressions:5d} clk={m.clicks:3d} "
                  f"cost=¥{m.cost_micros/1e6:.1f}")
    except Exception as e:
        print(f"  搜索词查询失败: {str(e)[:100]}")
