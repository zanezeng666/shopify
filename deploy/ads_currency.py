# -*- coding: utf-8 -*-
"""查账户货币与时区（只读）。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
rows = gas.search(customer_id=CID, query=(
    "SELECT customer.descriptive_name, customer.currency_code, "
    "customer.time_zone FROM customer"))
for r in rows:
    c = r.customer
    print(f"{c.descriptive_name} | 货币={c.currency_code} | 时区={c.time_zone}")
