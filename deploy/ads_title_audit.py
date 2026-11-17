# -*- coding: utf-8 -*-
"""标题审计：为什么出现 "Styles: Jbl Flip 4 / Craftsman Nextec /
Bose Soundlink Mini" 旧品类型标题。查四方：PMax 资产组文本资产、
Search 广告类型+自动生成标记、资产自动化设置、线上旧品存量。"""
import os
import sys

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608
SEARCH = 24448362668
BAD_WORDS = ("jbl", "bose", "craftsman", "styles")

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
rows = lambda q: list(gas.search(customer_id=CID, query=q))  # noqa


def run(label, fn):
    print(f"=== {label} ===")
    try:
        fn()
    except Exception as e:  # noqa
        msg = str(e)
        hints = [ln for ln in msg.split("\n")
                 if "Unrecognized" in ln or "error" in ln.lower()
                 or "Message" in ln]
        print(f"  查询失败: {hints[:2] or msg[:200]}")


# ---- 1. PMax 资产组文本资产全量 ----
def pmax_assets():
    n = hit = 0
    for r in rows(
        "SELECT asset_group_asset.asset_type, asset_group_asset.status, "
        "asset.resource_name, asset.name, asset.text_asset.text "
        f"FROM asset_group_asset WHERE campaign.id = {PMAX}"
    ):
        aga = r.asset_group_asset
        txt = (r.asset.text_asset.text or "").strip() if r.asset else ""
        n += 1
        low = txt.lower()
        mark = "  ◀◀◀" if any(w in low for w in BAD_WORDS) else ""
        if mark:
            hit += 1
        if mark or n <= 8 or aga.asset_type.name not in (
                "HEADLINE", "LONG_HEADLINE", "DESCRIPTION", "TEXT"):
            print(f"  [{aga.asset_type.name:14}] {aga.status.name:8} "
                  f"{txt[:80]!r}{mark}")
    print(f"  共 {n} 个资产组资产，含旧品牌词 {hit} 个")


run("PMax 资产组资产（asset_group_asset）", pmax_assets)


# ---- 2. Search 广告类型 + 自动生成标记 ----
def search_ads():
    for r in rows(
        "SELECT ad_group_ad.ad.type, ad_group_ad.ad.added_by_google_ads, "
        "ad_group_ad.ad.name, ad_group_ad.status, ad_group.name "
        f"FROM ad_group_ad WHERE campaign.id = {SEARCH}"
    ):
        a = r.ad_group_ad
        auto = a.ad.added_by_google_ads
        print(f"  {r.ad_group.name[:24]:24} type={a.ad.type.name:24} "
              f"auto={auto} [{a.status.name}]")


run("Search 广告类型与自动生成标记", search_ads)


# ---- 3. 资产自动化设置（PMax 文本自动化/最终 URL 扩展）----
def auto_settings():
    for q in (
        "SELECT asset_automation_setting.asset_field_type, "
        "asset_automation_setting.asset_automation_enrollment_status, "
        "campaign.name "
        f"FROM asset_automation_setting WHERE campaign.id = {PMAX}",
    ):
        for r in rows(q):
            s = r.asset_automation_setting
            print(f"  {s.asset_field_type.name}: "
                  f"{s.asset_automation_enrollment_status.name}")


run("PMax 资产自动化设置", auto_settings)


# ---- 4. 线上旧品存量（镜像库）----
def legacy_online():
    sys.path.insert(0, "/home/jason/shopify-admin/src")
    from sqlalchemy import text as sql

    from shopify_admin.core.database import get_engine
    eng = get_engine()
    with eng.connect() as c:
        tot = c.execute(sql(
            "SELECT COUNT(*) FROM products WHERE status='active'"
        )).scalar()
        med = c.execute(sql(
            "SELECT COUNT(*) FROM products WHERE status='active' "
            "AND product_type='Medical Battery'")).scalar()
        print(f"  线上 active 总数: {tot}，其中 Medical Battery: {med}，"
              f"非医疗旧品: {tot - med}")
        print("\n  -- 非医疗 active 的 product_type 分布 top12 --")
        for t, n in c.execute(sql(
            "SELECT product_type, COUNT(*) n FROM products "
            "WHERE status='active' AND "
            "(product_type IS NULL OR product_type<>'Medical Battery') "
            "GROUP BY product_type ORDER BY n DESC LIMIT 12"
        )):
            print(f"    {str(t)[:46]:46} {n}")
        print("\n  -- JBL/Bose/Craftsman 在售商品抽样 --")
        for h, t in c.execute(sql(
            "SELECT handle, title FROM products WHERE status='active' AND "
            "(LOWER(title) LIKE '%jbl%' OR LOWER(title) LIKE '%bose%' "
            "OR LOWER(title) LIKE '%craftsman%') LIMIT 6"
        )):
            print(f"    {t[:70]}")


run("线上旧品存量（镜像库，仅参考）", legacy_online)
