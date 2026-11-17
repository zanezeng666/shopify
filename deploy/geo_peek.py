# -*- coding: utf-8 -*-
"""侦察全部 ENABLED campaign 的 geo/语言定向现状 + PMax 画像信号现状"""
import os

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")

from google.ads.googleads.client import GoogleAdsClient

ads = GoogleAdsClient.load_from_dict({
    "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "unused"),
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", CID),
    "use_proto_plus": True,
})
gac = ads.get_service("GoogleAdsService")

# 1) ENABLED campaigns
enabled = {}
q0 = ("SELECT campaign.id, campaign.name, campaign.advertising_channel_type "
      "FROM campaign WHERE campaign.status = 'ENABLED'")
for row in gac.search(customer_id=CID, query=q0):
    enabled[row.campaign.id] = (row.campaign.name,
                                row.campaign.advertising_channel_type.name)
print(f"ENABLED campaigns: {len(enabled)}")

# 2) 每个 campaign 的 LOCATION / LANGUAGE criteria
crit = {}
q1 = ("SELECT campaign_criterion.campaign, campaign_criterion.type, "
      "campaign_criterion.location.geo_target_constant, "
      "campaign_criterion.language.language_constant, "
      "campaign_criterion.negative "
      "FROM campaign_criterion "
      "WHERE campaign_criterion.type IN ('LOCATION', 'LANGUAGE')")
loc_cnt = lang_cnt = 0
for row in gac.search(customer_id=CID, query=q1):
    cid_ = int(row.campaign_criterion.campaign.split("/")[-1])
    cc = row.campaign_criterion
    crit.setdefault(cid_, []).append(cc)
    if cc.type_.name == "LOCATION":
        loc_cnt += 1
    else:
        lang_cnt += 1
print(f"\nLOCATION criteria 总数: {loc_cnt} | LANGUAGE criteria 总数: {lang_cnt}")
no_loc = [c for c in enabled if not any(
    cc.type_.name == "LOCATION" and not cc.negative for cc in crit.get(c, []))]
print(f"无正向 LOCATION 定位的 campaign 数: {len(no_loc)} "
      f"(=默认全球投放)")
no_us = []
for c in enabled:
    has_us = any(cc.type_.name == "LOCATION" and not cc.negative and
                 (cc.location.geo_target_constant or "").endswith("/2840")
                 for cc in crit.get(c, []))
    has_en = any(cc.type_.name == "LANGUAGE" and not cc.negative and
                 (cc.language.language_constant or "").endswith("/1000")
                 for cc in crit.get(c, []))
    if not has_us or not has_en:
        no_us.append((c, enabled[c][1], has_us, has_en))
print(f"\nENABLED 中缺 US(2840) 或缺 English(1000) 的 campaign: {len(no_us)}")
for c, ch, us, en in no_us:
    print(f"  {c} [{ch:16s}] US={'Y' if us else '缺'} EN={'Y' if en else '缺'} {enabled[c][0][:32]}")

# 3) PMax audience signals 现状
print("\nPMax 24441391608 audience signals:")
try:
    q2 = ("SELECT asset_group_signal.asset_group, "
          "asset_group_signal.audience "
          "FROM asset_group_signal WHERE campaign.id = 24441391608")
    rows = list(gac.search(customer_id=CID, query=q2))
    if not rows:
        print("  (无任何画像信号)")
    for r in rows:
        print(f"  ag={r.asset_group_signal.asset_group.split('/')[-1]} "
              f"aud={r.asset_group_signal.audience}")
except Exception as e:
    print("  query failed:", str(e)[:200])
