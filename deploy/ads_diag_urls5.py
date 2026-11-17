# -*- coding: utf-8 -*-
"""诊断 v7（收尾）：跟踪模板 + 落地页 HTTP 复测。"""
import os

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608
SEARCH = 24448362668

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
rows = lambda q: list(gas.search(customer_id=CID, query=q))  # noqa

print("=== 跟踪模板/URL 后缀 ===")
for r in rows(
    "SELECT campaign.id, campaign.name, campaign.tracking_url_template, "
    "campaign.final_url_suffix, campaign.url_custom_parameters "
    "FROM campaign WHERE campaign.status != 'REMOVED'"
):
    c = r.campaign
    print(f"  [{c.id}] {c.name[:30]}")
    print(f"    tracking={c.tracking_url_template or '-'}")
    print(f"    suffix={c.final_url_suffix or '-'}")
for r in rows(
    "SELECT customer.tracking_url_template, customer.final_url_suffix "
    "FROM customer"
):
    print(f"  账号级 tracking={r.customer.tracking_url_template or '-'} "
          f"suffix={r.customer.final_url_suffix or '-'}")

print("\n=== 落地页 HTTP 复测（限流窗口已过）===")
with httpx.Client(
    timeout=25, follow_redirects=True,
    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
              "AppleWebKit/537.36 Chrome/120 Safari/537.36"},
) as hc:
    for u in (
        "https://www.estrybattery.com/",
        "https://www.estrybattery.com/collections/medical-battery",
    ):
        try:
            r = hc.get(u)
            title = ""
            if "<title" in r.text.lower():
                s = r.text.lower().index("<title")
                title = r.text[s:s + 120].replace("\n", " ")[:100]
            print(f"  {r.status_code} {u} | {title}")
        except Exception as e:  # noqa
            print(f"  ERR {u} {type(e).__name__}: {e}")
