# -*- coding: utf-8 -*-
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
r = httpx.post(
    "https://googleads.googleapis.com/v26/customers/7059800494/googleAds:searchStream",
    headers=H, json={"query": "SELECT customer.time_zone, customer.currency_code, customer.descriptive_name FROM customer"},
    timeout=30)
print(r.json()[0]["results"][0]["customer"])
