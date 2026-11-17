# -*- coding: utf-8 -*-
"""TARGET_SPEND 出价上限(portfolio) + system_serving_status + 60天展示面 + 渠道对比"""
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

print("=== ① portfolio bidding_strategy（TARGET_SPEND 出价上限） ===")
q = ("SELECT bidding_strategy.id, bidding_strategy.name, "
     "bidding_strategy.type, bidding_strategy.target_spend.target_spend_micros, "
     "bidding_strategy.target_spend.cpc_bid_ceiling_micros "
     "FROM bidding_strategy")
for row in gac.search(customer_id=CID, query=q):
    b = row.bidding_strategy
    ts = b.target_spend
    print(f"  [{b.id}] {b.name[:30]:30s} 类型={b.type_.name if b.type_ else '?'} "
          f"目标支出=¥{(ts.target_spend_micros or 0)/1e6:.2f} "
          f"CPC上限=¥{(ts.cpc_bid_ceiling_micros or 0)/1e6:.2f}")

print("\n=== ② Medical Search 关键词 system_serving_status 分布 ===")
q3 = ("SELECT ad_group_criterion.system_serving_status "
      "FROM ad_group_criterion WHERE campaign.id = 24448362668 "
      "AND ad_group_criterion.type = 'KEYWORD'")
ss = {}
for row in gac.search(customer_id=CID, query=q3):
    name = row.ad_group_criterion.system_serving_status.name
    ss[name] = ss.get(name, 0) + 1
print(f"  {ss}")

print("\n=== ③ 全部 ENABLED Search 系列关键词 serving 汇总（抽样 Medical+Speaker） ===")
for cid_ in (24448362668, 24453830877):
    q3b = ("SELECT ad_group_criterion.keyword.text, "
           "ad_group_criterion.system_serving_status "
           f"FROM ad_group_criterion WHERE campaign.id = {cid_} "
           "AND ad_group_criterion.type = 'KEYWORD' LIMIT 6")
    print(f"  -- campaign {cid_} 样例:")
    for row in gac.search(customer_id=CID, query=q3b):
        print(f"     {row.ad_group_criterion.keyword.text[:30]:30s} "
              f"{row.ad_group_criterion.system_serving_status.name}")

print("\n=== ④ Medical Search 60 天有过展示的关键词数 ===")
q2 = ("SELECT ad_group_criterion.keyword.text, metrics.impressions, "
      "metrics.clicks, metrics.cost_micros "
      "FROM keyword_view WHERE campaign.id = 24448362668 "
      "AND segments.date BETWEEN '2026-09-14' AND '2026-11-13'")
kws = list(gac.search(customer_id=CID, query=q2))
shown = [r for r in kws if r.metrics.impressions > 0]
print(f"  60 天有展示: {len(shown)}/{len(kws)} 个关键词")
for r in sorted(shown, key=lambda r: -r.metrics.impressions)[:8]:
    print(f"    {r.ad_group_criterion.keyword.text[:32]:32s} imp={r.metrics.impressions} "
          f"clk={r.metrics.clicks} cost=¥{r.metrics.cost_micros/1e6:.2f}")

print("\n=== ⑤ 60 天各渠道消耗对比 ===")
q4 = ("SELECT campaign.advertising_channel_type, metrics.cost_micros, "
      "metrics.clicks, metrics.impressions "
      "FROM campaign WHERE segments.date BETWEEN '2026-09-14' AND '2026-11-13' "
      "AND campaign.status = 'ENABLED'")
agg = {}
for row in gac.search(customer_id=CID, query=q4):
    t = row.campaign.advertising_channel_type.name
    a = agg.setdefault(t, [0, 0, 0])
    a[0] += row.metrics.cost_micros; a[1] += row.metrics.clicks
    a[2] += row.metrics.impressions
for t, (cost, clk, imp) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
    print(f"  {t:12s} 60天: cost=¥{cost/1e6:9.1f} clk={clk:6d} imp={imp:8d}")
