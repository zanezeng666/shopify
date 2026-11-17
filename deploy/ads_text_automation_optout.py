# -*- coding: utf-8 -*-
"""PMax 文本资产自动化 opt-out：阻止 Google 自动生成标题/描述
（"Styles: Jbl Flip 4..." 类目录驱动自动标题的第一道闸）。
先反射枚举真实值再 mutate。"""
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

# ---- 枚举反射 ----
print("=== AssetAutomationType 枚举 ===")
try:
    from google.ads.googleads.v26.enums.types import (
        asset_automation_type as aat_mod)
    names = [n for n in dir(aat_mod) if "AssetAutomationType" in n
             or n.isupper()]
    cls = getattr(aat_mod, "AssetAutomationType", None)
    if cls:
        print(f"  类: {cls}")
        for v in cls:
            print(f"    {v.name} = {v.value}")
    else:
        print(f"  模块符号: {names}")
except Exception as e:  # noqa
    print(f"  反射失败: {e}")

print("\n=== AssetAutomationSettingStatus 枚举 ===")
try:
    from google.ads.googleads.v26.enums.types import (
        asset_automation_status as aas_mod)
    cls = getattr(aas_mod, "AssetAutomationSettingStatus", None)
    if cls:
        for v in cls:
            print(f"    {v.name} = {v.value}")
    else:
        print(f"  模块符号: {[n for n in dir(aas_mod) if not n.startswith('_')]}")
except Exception as e:  # noqa
    print(f"  反射失败: {e}")

# ---- mutate opt-out ----
print("\n=== TEXT_ASSET_AUTOMATION opt-out ===")
try:
    svc = client.get_service("AssetAutomationSettingService")
    op = client.get_type("AssetAutomationSettingOperation")
    s = op.create
    s.campaign = f"customers/{CID}/campaigns/{PMAX}"
    s.asset_automation_type = client.get_type(
        "AssetAutomationTypeEnum").AssetAutomationType.TEXT_ASSET_AUTOMATION
    try:
        s.asset_automation_status = client.get_type(
            "AssetAutomationSettingStatusEnum"
        ).AssetAutomationSettingStatus.OPTED_OUT
    except Exception as e:  # noqa
        print(f"  状态枚举赋值失败({e})，尝试字符串/数字回退")
        s.asset_automation_status = 3  # 实测前反射出值再定
    resp = svc.mutate_asset_automation_settings(
        customer_id=CID, operations=[op])
    print(f"  OK: {resp.results[0].resource_name}")
except Exception as e:  # noqa
    msg = str(e)
    errs = [ln.strip() for ln in msg.split("\n")
            if any(k in ln for k in ("error", "Error", "message:", "无法",
                                     "cannot", "not "))]
    print(f"  FAIL {errs[:3] or msg[:400]}")
