# -*- coding: utf-8 -*-
"""Search 系列 CPC 上限 ¥1.50 → ¥5.00（仅 Maximize Clicks 策略；PMax 不受影响）"""
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
bs_svc = ads.get_service("BiddingStrategyService")

NEW_CEIL = 5_000_000  # ¥5.00 = 5,000,000 micros（账户货币 CNY）

# ① 读全部 Maximize Clicks 策略现状
q = ("SELECT bidding_strategy.id, bidding_strategy.name, "
     "bidding_strategy.type, "
     "bidding_strategy.target_spend.cpc_bid_ceiling_micros "
     "FROM bidding_strategy WHERE bidding_strategy.type = 'TARGET_SPEND'")
rows = list(gac.search(customer_id=CID, query=q))
print(f"MaxClicks 策略数={len(rows)}")
for r in rows:
    b = r.bidding_strategy
    ceil = b.target_spend.cpc_bid_ceiling_micros
    print(f"  [{b.id}] {b.name[:40]:40s} 现上限=¥{(ceil or 0)/1e6:.2f}")

# ② 提价 ¥1.50 → ¥5.00
ops, touched = [], []
for r in rows:
    b = r.bidding_strategy
    if b.target_spend.cpc_bid_ceiling_micros == NEW_CEIL:
        continue
    op = ads.get_type("BiddingStrategyOperation")
    op.update.resource_name = f"customers/{CID}/biddingStrategies/{b.id}"
    op.update.target_spend.cpc_bid_ceiling_micros = NEW_CEIL
    op.update_mask.paths.append("target_spend.cpc_bid_ceiling_micros")
    ops.append(op)
    touched.append(b.id)

if not ops:
    print("已是目标值，无需改动")
else:
    resp = bs_svc.mutate_bidding_strategies(customer_id=CID, operations=ops)
    print(f"已更新 {len(resp.results)} 个策略: {touched}")

# ③ 读回验证 + 覆盖系列数核对
rows2 = list(gac.search(customer_id=CID, query=q))
for r in rows2:
    b = r.bidding_strategy
    v = b.target_spend.cpc_bid_ceiling_micros
    ok = "OK" if v == NEW_CEIL else "FAIL"
    print(f"  复核[{b.id}] ¥{(v or 0)/1e6:.2f} {ok}")

q2 = ("SELECT campaign.id, campaign.bidding_strategy FROM campaign "
      "WHERE campaign.advertising_channel_type = 'SEARCH' "
      "AND campaign.status = 'ENABLED'")
cs = list(gac.search(customer_id=CID, query=q2))
n = sum(1 for r in cs if r.campaign.bidding_strategy)
print(f"受影响 ENABLED Search 系列数={len(cs)}（挂出价策略 {n} 个）")
