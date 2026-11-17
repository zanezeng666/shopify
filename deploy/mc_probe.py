# -*- coding: utf-8 -*-
"""GET shopping campaign 对象找 merchantCenterId (安全版)。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

CID = "7059800494"
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]

for camp in (10333143072, 10418745336):
    r = httpx.get(
        f"https://googleads.googleapis.com/v25/customers/{CID}/campaigns/"
        f"{camp}", headers={"Authorization": f"Bearer {at}"}, timeout=30)
    print(camp, "HTTP", r.status_code, "|", r.text[:220].replace("\n", " "))
