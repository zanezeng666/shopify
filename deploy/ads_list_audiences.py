# -*- coding: utf-8 -*-
"""audience 全量 + 完整报错抓取。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = f"customers/{CID}/assetGroups/6770847164"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

rows = list(gas.search(customer_id=CID, query=(
    "SELECT audience.id, audience.name, audience.status FROM audience")))
print(f"audience 资源全量: {len(rows)} 个")
for r in rows:
    a = r.audience
    print(f"  #{a.id} | {a.name} | {a.status.name if a.status else '?'}")

print("\n=== 重试挂信号并抓完整错误 ===")
ags = client.get_service("AssetGroupSignalService")
op = client.get_type("AssetGroupSignalOperation")
sig = op.create
sig.asset_group = AG
sig.audience.audience = f"customers/{CID}/audiences/7248682486"
try:
    res = ags.mutate_asset_group_signals(customer_id=CID, operations=[op])
    print("成功:", res.results[0].resource_name)
except Exception as e:  # noqa: BLE001
    errs = getattr(e, "errors", None)
    if errs:
        for er in errs:
            print("ERR:", (er.message or "")[:300],
                  "| loc:", er.location)
    else:
        print("失败:", str(e)[:500])
