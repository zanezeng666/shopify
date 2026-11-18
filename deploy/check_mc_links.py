"""MC 136469408 的 adsLinks：链接的全部 Google Ads 账户。只读。"""
import os

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

import httpx

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}

# Content API v2.1 accounts.get（含 adsLinks）
r = httpx.get("https://shoppingcontent.googleapis.com/content/v2.1/136469408/accounts/136469408",
              headers=H, timeout=30)
print(f"HTTP {r.status_code}")
if r.status_code == 200:
    j = r.json()
    print(f"MC name: {j.get('name')!r}")
    links = j.get("adsLinks") or []
    print(f"adsLinks {len(links)} 条：")
    for l in links:
        print(f"  Ads CID: {l.get('adsId') or l.get('id')}  status: {l.get('status')}")
    if not links:
        print("  （无 adsLinks 字段或为空）")
else:
    print(r.text[:200])
