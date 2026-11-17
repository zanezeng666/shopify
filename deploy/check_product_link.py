# -*- coding: utf-8 -*-
"""ProductLinkService.list 查 Ads↔MC link"""
import os

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")

from google.ads.googleads.client import GoogleAdsClient

ads = GoogleAdsClient.load_from_dict({
    "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "unused"),
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", CID),
    "use_proto_plus": True,
})
svc = ads.get_service("ProductLinkService")
req = ads.get_type("ListProductLinksRequest")
req.customer_id = CID
resp = svc.list_product_links(request=req)
for pl in resp.product_links:
    mc = pl.merchant_center.merchant_id if pl.merchant_center else None
    print(f"  link={pl.product_link_id} status={pl.status.name if pl.status else '?'} "
          f"merchant={mc}")
