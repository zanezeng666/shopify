# -*- coding: utf-8 -*-
"""PMax 无效链接诊断 v3：asset_group final_urls + 各类型资产政策状态 + HTTP 实测。
sitelink/page_feed 的 URL 值 GAQL 不可查，若其政策异常再走 mutate 修复。"""
import os

import httpx
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


def rows(q):
    return list(gas.search(customer_id=CID, query=q))


urls = {}

# 1) 资产组 final_urls
for r in rows(
    "SELECT asset_group.id, asset_group.name, asset_group.final_urls, "
    "asset_group.status "
    f"FROM asset_group WHERE campaign.id = {PMAX}"
):
    g = r.asset_group
    for u in g.final_urls or []:
        urls.setdefault(u, []).append(
            f"asset_group[{g.name}/{g.status.name}]")

# 2) 关联资产：字段类型+名称+政策状态
print("=== PMax 关联资产清单 ===")
asset_rns = []
for tbl, extra in (
    ("campaign_asset", None),
    ("asset_group_asset", "asset_group_asset.field_type"),
):
    for r in rows(
        f"SELECT campaign.id, {tbl}.asset"
        + (f", {extra}" if extra else "")
        + f", {tbl}.status FROM {tbl} WHERE campaign.id = {PMAX}"
    ):
        t = getattr(r, tbl)
        ft = t.field_type.name if extra else "campaign级"
        asset_rns.append(t.asset)
        print(f"  {tbl[:8]} {ft:22} status={t.status.name:9} {t.asset}")

in_list = ", ".join(f'"{n}"' for n in dict.fromkeys(asset_rns))
for r in rows(
    "SELECT asset.resource_name, asset.name, asset.type, "
    "asset.policy_summary.approval_status, "
    "asset.policy_summary.policy_topic_entries "
    f"FROM asset WHERE asset.resource_name IN ({in_list})"
):
    a = r.asset
    st = a.policy_summary.approval_status.name if a.policy_summary else "-"
    ents = "; ".join(
        f"{e.type_}/{e.entry_type.name}" for e in
        (a.policy_summary.policy_topic_entries if a.policy_summary else []))
    flag = "" if st in ("APPROVED", "UNSPECIFIED") else "  ◀◀ 政策异常"
    print(f"  asset {a.type.name:16} {st:16} {a.name[:50]}{flag} {ents[:60]}")

# 3) HTTP 实测资产组 final_urls
print(f"\n=== HTTP 实测 {len(urls)} 个资产组 URL ===")
bad = []
with httpx.Client(
    timeout=20, follow_redirects=True,
    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
              "AppleWebKit/537.36 Chrome/120 Safari/537.36"},
) as hc:
    for u, srcs in urls.items():
        try:
            r = hc.get(u)
            code, loc, body = r.status_code, str(r.url), r.text[:4000]
            body_ok = "estry" in body.lower() or "battery" in body.lower()
        except Exception as e:  # noqa
            code, loc, body_ok = f"ERR:{type(e).__name__}", u, False
        ok = code == 200 and body_ok
        print(f"[{'OK ' if ok else 'BAD'}] {code} {u} <- {srcs}"
              + ("" if loc == u else f"  (→ {loc[:100]})"))
        if not ok:
            bad.append((u, srcs, code))

print(f"\n=== 资产组 URL 异常 {len(bad)} 个 ===")
for u, srcs, code in bad:
    print(f"  {code} {u} | {srcs}")
