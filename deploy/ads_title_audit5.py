# -*- coding: utf-8 -*-
"""proto 反射 AssetAutomationSetting 真实字段 + 查询 PMax 自动化状态。"""
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

print("=== Campaign 内嵌 AssetAutomationSetting 字段反射 ===")
from google.ads.googleads.v26.resources.types import (  # noqa: E402
    campaign as camp_mod)

for attr in ("AssetAutomationSetting",):
    cls = getattr(camp_mod.Campaign, attr, None)
    if cls is None:
        # proto-plus 嵌套消息在 _meta
        print(f"  Campaign 无 {attr} 属性，查 _meta")
        continue
    try:
        for fname in cls.meta.fields:
            print(f"  {attr}.{fname}")
    except Exception as e:  # noqa
        print(f"  反射失败 {e}")

# 也试独立资源模块
try:
    from google.ads.googleads.v26.resources.types import (
        asset_automation_setting as aas_mod)
    for fname in aas_mod.AssetAutomationSetting.meta.fields:
        print(f"  独立资源 AssetAutomationSetting.{fname}")
except ImportError:
    print("  (无独立资源模块)")
except Exception as e:  # noqa
    print(f"  独立资源反射失败: {e}")

print("\n=== PMax campaign 自动化设置查询 ===")
for q in (
    "SELECT campaign.asset_automation_settings.asset_automation_type "
    f"FROM campaign WHERE campaign.id = {PMAX}",
    "SELECT campaign.name, "
    "campaign.asset_automation_settings.asset_automation_type, "
    "campaign.asset_automation_settings.asset_automation_enrollment "
    f"FROM campaign WHERE campaign.id = {PMAX}",
):
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"OK rows={len(rs)}")
        for r in rs:
            for s in (r.campaign.asset_automation_settings or []):
                extra = ""
                try:
                    extra = f" enrollment={s.asset_automation_enrollment}"
                except AttributeError:
                    try:
                        extra = (f" status="
                                 f"{s.asset_automation_enrollment_status}")
                    except AttributeError:
                        pass
                print(f"  {s.asset_automation_type.name}{extra}")
        break
    except Exception as e:  # noqa
        msg = str(e)
        errs = [ln.strip() for ln in msg.split("\n")
                if "Unrecognized" in ln or "message:" in ln.lower()]
        print(f"FAIL {errs[:1] or msg[:200]}")
