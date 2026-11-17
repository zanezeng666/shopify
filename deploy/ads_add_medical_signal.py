# -*- coding: utf-8 -*-
"""给 PMax Medical Estry 资产组挂搜索主题信号（gRPC google-ads 库）。

v26 实测内省结论：
- AssetGroupSignal.signal oneof = {audience(AudienceInfo), search_theme(SearchThemeInfo), ...}
- search_theme 是 PMax 专属关键词意图信号，纯文本一步到位（官方主推）；
  audience 路径须 CustomAudience→Audience 资源包装，链长坑多，不采用。
- CustomAudienceType = {AUTO, INTEREST, PURCHASE_INTENT, SEARCH}（无 CUSTOM_INTENT）。

断点/幂等: deploy/med_signal.json + 建前 GAQL 查线上已挂 search_theme 去重。
"""
import json
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
DEP = "/home/jason/shopify-admin/deploy"
AG = f"customers/{CID}/assetGroups/6770847164"
STATE = f"{DEP}/med_signal.json"

SIGNAL_TERMS = [
    "medical device battery replacement",
    "patient monitor battery",
    "defibrillator battery",
    "infusion pump battery",
    "medical equipment repair battery",
    "biomedical equipment battery",
    "nihon kohden battery",
    "welch allyn battery",
    "mindray battery",
    "ge medical battery",
]

state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
state.setdefault("themes", [])  # 已挂成功的 search theme 文本


def save():
    json.dump(state, open(STATE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def main() -> None:
    client = GoogleAdsClient.load_from_dict({
        "developer_token": "unused",
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "use_proto_plus": True,
    })

    gas = client.get_service("GoogleAdsService")

    # 1) 线上已有 signals 查询（幂等去重）
    q = ("SELECT asset_group_signal.resource_name, "
         "asset_group_signal.search_theme.text, "
         "asset_group_signal.approval_status "
         "FROM asset_group_signal "
         f"WHERE asset_group_signal.asset_group='{AG}'")
    existing = {}
    for row in gas.search(customer_id=CID, query=q):
        sig = row.asset_group_signal
        text = sig.search_theme.text if sig.search_theme else ""
        existing[text] = sig.resource_name
        print("existing signal:", text or "(non-theme)",
              "| status:", sig.approval_status.name)
    todo = [t for t in SIGNAL_TERMS
            if t not in existing and t not in state["themes"]]
    print(f"themes to create: {len(todo)}/{len(SIGNAL_TERMS)}")

    # 2) 批量挂 search_theme 信号
    if todo:
        svc = client.get_service("AssetGroupSignalService")
        ops = []
        for t in todo:
            op = client.get_type("AssetGroupSignalOperation")
            sig = op.create
            sig.asset_group = AG
            sig.search_theme.text = t
            ops.append(op)
        resp = svc.mutate_asset_group_signals(
            customer_id=CID, operations=ops)
        for r in resp.results:
            print("created:", r.resource_name)
        state["themes"].extend(todo)
        save()

    # 3) readback
    print("=== readback ===")
    for row in gas.search(customer_id=CID, query=q):
        sig = row.asset_group_signal
        if sig.search_theme:
            print("live theme:", sig.search_theme.text,
                  "| status:", sig.approval_status.name)

    print("=== PMax 搜索主题信号完成 ===")


if __name__ == "__main__":
    main()
