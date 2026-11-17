# -*- coding: utf-8 -*-
"""最后试探：userLists 路径直塞 audience 字段。"""
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
ags = client.get_service("AssetGroupSignalService")

REFS = [
    ("userLists 路径", f"customers/{CID}/userLists/7248682486"),
    ("audiences 路径(小写复检)", f"customers/{CID}/audiences/7248682486"),
]
for label, ref in REFS:
    op = client.get_type("AssetGroupSignalOperation")
    sig = op.create
    sig.asset_group = AG
    sig.audience.audience = ref
    try:
        res = ags.mutate_asset_group_signals(customer_id=CID, operations=[op])
        print(f"[OK] {label}: {res.results[0].resource_name}")
        break
    except Exception as e:  # noqa: BLE001
        errs = getattr(e, "errors", [])
        codes = [er.error_code for er in errs]
        print(f"[FAIL] {label}: {[str(c) for c in codes][:1]}")
