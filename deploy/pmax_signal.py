# -*- coding: utf-8 -*-
"""PMax 画像信号：查 in-market 医疗相关受众 → 挂到 asset_group 6770847164"""
import os

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")
CAMP = "24441391608"
AG = "6770847164"

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

print("=== in-market 医疗相关受众候选 ===")
cands = []
seen = set()
for kw in ("medical", "hospital", "diagnostic"):
    q = ("SELECT user_interest.user_interest_id, user_interest.name "
         f"FROM user_interest WHERE user_interest.name LIKE '%{kw}%'")
    for row in gac.search(customer_id=CID, query=q):
        ui = row.user_interest
        if ui.user_interest_id not in seen:
            seen.add(ui.user_interest_id)
            cands.append((ui.user_interest_id, ui.name))
            print(f"  {ui.user_interest_id}: {ui.name}")

if not cands:
    print("  (无候选)")
    raise SystemExit()

# 挂前3个最相关的作为 audience signal
ags = ads.get_service("AssetGroupSignalService")
ops = []
for uid, name in cands[:3]:
    sig = ads.get_type("AssetGroupSignal")
    sig.asset_group = f"customers/{CID}/assetGroups/{CAMP}~{AG}"
    sig.audience = f"customers/{CID}/userInterests/{uid}"
    op = ads.get_type("AssetGroupSignalOperation")
    op.create = sig
    ops.append(op)
    print(f"  → 加 signal: {name}")
try:
    r = ags.mutate_asset_group_signals(customer_id=CID, operations=ops)
    for res in r.results:
        print(f"  signal OK: {res.resource_name}")
except Exception as e:
    print("  signal failed:", str(e)[:300])
