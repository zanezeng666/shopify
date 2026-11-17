# -*- coding: utf-8 -*-
"""最终确认：asset_automation_setting 独立资源（正确字段组合）。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

for q in (
    "SELECT asset_automation_setting.asset_automation_type, "
    "asset_automation_setting.asset_automation_status, campaign.name "
    f"FROM asset_automation_setting WHERE campaign.id = {PMAX}",
    "SELECT asset_automation_setting.asset_automation_type, "
    "asset_automation_setting.asset_automation_status "
    "FROM asset_automation_setting",
):
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"OK rows={len(rs)}")
        for r in rs:
            s = r.asset_automation_setting
            print(f"  {s.asset_automation_type.name}: "
                  f"{s.asset_automation_status.name} "
                  f"({r.campaign.name[:30] if r.campaign.name else ''})")
        break
    except Exception as e:  # noqa
        msg = str(e)
        errs = [ln.strip() for ln in msg.split("\n")
                if "Unrecognized" in ln or "message:" in ln.lower()]
        print(f"FAIL {errs[:1] or msg[:200]}")
