# -*- coding: utf-8 -*-
"""审计全部 ENABLED campaign 的地理定位：找出任何非 US 正定位/负定位情况。"""
import os
from collections import defaultdict

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

rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name, campaign.advertising_channel_type, "
    "campaign_criterion.negative, "
    "campaign_criterion.location.geo_target_constant "
    "FROM campaign_criterion WHERE campaign.status = 'ENABLED' "
    "AND campaign_criterion.type = 'LOCATION'"))
by_camp = defaultdict(list)
for r in rows:
    cc = r.campaign_criterion
    by_camp[(r.campaign.id, r.campaign.name,
             r.campaign.advertising_channel_type.name)].append(
        ("负" if cc.negative else "正", cc.location.geo_target_constant))

no_geo = []
for cid_, name, ctype in by_camp:
    pass
bad = 0
for (cid_, name, ctype), locs in sorted(by_camp.items()):
    pos = [g for tag, g in locs if tag == "正"]
    non_us_pos = [g for g in pos if not g.endswith("/2840")]
    flag = ""
    if non_us_pos:
        flag = f"  <-- 有非US正定位: {non_us_pos}"
        bad += 1
    if not pos:
        flag = "  <-- 无任何正定位(全球投放)"
        bad += 1
    print(f"[{ctype[:6]}] {name[:44]:<44} id={cid_} "
          f"{'/'.join(t + g.split('/')[-1] for t, g in locs) or '-'}{flag}")

# 无任何 location criterion 的 campaign（= 全球投放）
all_rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name, campaign.advertising_channel_type "
    "FROM campaign WHERE campaign.status = 'ENABLED'"))
have = {c[0] for c in by_camp}
for r in all_rows:
    if r.campaign.id not in have:
        print(f"[{r.campaign.advertising_channel_type.name[:6]}] "
              f"{r.campaign.name[:44]:<44} id={r.campaign.id}   "
              f"<== 零地理定位=全球投放")
        bad += 1
print(f"\n结论: {len(by_camp)} 个有定位 series 中异常 {bad} 处")
