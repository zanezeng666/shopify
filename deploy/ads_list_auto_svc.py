# -*- coding: utf-8 -*-
"""列出 google-ads 客户端全部含 automation 的服务+库版本。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})

try:
    from importlib.metadata import version
    print(f"google-ads 版本: {version('google-ads')}")
except Exception as e:  # noqa
    print(f"版本查询失败: {e}")
import importlib  # noqa: E402
import pkgutil  # noqa: E402

import google.ads.googleads.v26.services as svc_pkg  # noqa: E402

mods = [m.name for m in pkgutil.iter_modules(svc_pkg.__path__)
        if "automation" in m.name.lower() or "asset_auto" in m.name.lower()]
print(f"v26 services 含 automation/asset_auto 的模块: {mods or '无'}")

from google.ads.googleads.v26.enums.types import (  # noqa: E402
    asset_automation_status as aas_mod)

for v in aas_mod.AssetAutomationStatusEnum.AssetAutomationStatus:
    print(f"  status: {v.name} = {v.value}")
