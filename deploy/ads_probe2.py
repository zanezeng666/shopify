# -*- coding: utf-8 -*-
"""侦察2: PMax系列的MC链接/转化动作/env键值/账户链接的MC清单。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}",
     "Content-Type": "application/json", "developer-token": "unused"}
CID = "7059800494"


def gql(q):
    r = httpx.post(
        f"https://googleads.googleapis.com/v25/customers/{CID}/"
        "googleAds:searchStream", headers=H, json={"query": q}, timeout=30)
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    for b in rows:
        if "results" not in b:
            print("ERR:", str(b)[:300])
        for e in b.get("results", []):
            yield e


print("== PMax 系列购物设置 ==")
for e in gql(
    "SELECT campaign.id, campaign.name, campaign.status, "
    "campaign.shopping_setting.merchant_center_id, "
    "campaign.shopping_setting.sales_country, "
    "campaign.shopping_setting.feed_label "
    "FROM campaign WHERE campaign.advertising_channel_type "
    "= 'PERFORMANCE_MAX'"
):
    c = e["campaign"]
    ss = c.get("shoppingSetting", {})
    print(f"  {c['id']} [{c.get('status')}] {c['name'][:34]:<34} "
          f"MC={ss.get('merchantCenterId')} "
          f"国={ss.get('salesCountry')} feed={ss.get('feedLabel')}")

print("\n== 转化动作 ==")
for e in gql(
    "SELECT conversion_action.id, conversion_action.name, "
    "conversion_action.status, conversion_action.category "
    "FROM conversion_action"
):
    ca = e["conversionAction"]
    print(f"  {ca['id']} [{ca['status']}] {ca['name'][:40]} "
          f"({ca.get('category')})")

print("\n== 账户链接的 Merchant Center ==")
for e in gql(
    "SELECT merchant_center_link.id, merchant_center_link.status "
    "FROM merchant_center_link"
):
    print(" ", e)

print("\n== env 关键值 ==")
for k in ("GOOGLE_ADS_CUSTOMER_ID", "GOOGLE_ADS_CONVERSION_ACTION",
          "GOOGLE_CUSTOMER_ID"):
    print(f"  {k} = {os.environ.get(k)}")
