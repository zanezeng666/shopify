# -*- coding: utf-8 -*-
"""查 audience 资源列表（含医疗相关）"""
import os

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")

from google.ads.googleads.client import GoogleAdsClient

ads = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "login_customer_id": CID,
    "use_proto_plus": True,
})
gac = ads.get_service("GoogleAdsService")
q = ("SELECT audience.id, audience.name FROM audience")
n = 0
for row in gac.search(customer_id=CID, query=q):
    a = row.audience
    n += 1
    print(f"  {a.id} {a.name[:60]}")
    if n >= 20:
        print("  ...(前20)")
        break
if n == 0:
    print("  (该客户无 audience 资源)")
