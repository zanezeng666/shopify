import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
r = httpx.get(
    f"https://googleads.googleapis.com/v25/customers/{CID}/campaigns/24448362668",
    headers={"Authorization": f"Bearer {tok}", "developer-token": "unused"},
    timeout=60)
print(r.status_code)
d = r.json()
keep = {k: d[k] for k in d if k in (
    "name", "status", "advertisingChannelType", "biddingStrategy",
    "biddingStrategyType", "networkSettings", "targeting",
    "campaignBiddingStrategy", "startDate", "realTimeBiddingSetting")}
print(json.dumps(keep, indent=1, ensure_ascii=False))
print("TOP-KEYS:", sorted(d.keys())[:40])
