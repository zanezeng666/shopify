# -*- coding: utf-8 -*-
"""B2 最终版：HTTP API mutate，enum 用字符串名 LOCATION_OF_PRESENCE（绕开数值漂移）。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
CAMP = f"customers/{CID}/campaigns/24441391608"

tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
     "developer-token": "unused"}

r = httpx.post(f"https://googleads.googleapis.com/v26/customers/{CID}/campaigns:mutate",
               headers=H, json={"operations": [{
                   "update": {
                       "resourceName": CAMP,
                       "geoTargetTypeSetting": {
                           "positiveGeoTargetType": "PRESENCE"}},
                   "updateMask": "geoTargetTypeSetting.positiveGeoTargetType"}]},
               timeout=60)
print("HTTP", r.status_code)
print(r.text[:400])
