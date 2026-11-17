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
H = {"Authorization": f"Bearer {tok}", "developer-token": "unused",
     "Content-Type": "application/json"}
for gaql in (
    "SELECT campaign.name, campaign.network_settings.target_google_search, "
    "campaign.bidding_strategy FROM campaign WHERE campaign.status='ENABLED' LIMIT 1",
    "SELECT campaign.name, campaign.targeting.network_settings.target_google_search "
    "FROM campaign LIMIT 1",
):
    r = httpx.post(f"https://googleads.googleapis.com/v25/customers/{CID}"
                   "/googleAds:search", headers=H,
                   json={"query": gaql}, timeout=60)
    print(r.status_code, gaql[:70])
    if r.status_code == 200:
        print("  ->", r.json().get("results") or r.json().get("rows"))
    else:
        print("  ->", r.text[:200])
