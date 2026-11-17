# -*- coding: utf-8 -*-
"""MC 免费流量位：状态探测 → (如需) 申请激活 US；feed 健康核查。
Content API v2.1，MC=136469408，token 已含 content scope。"""
import os
import time
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MID = "136469408"
B = f"https://shoppingcontent.googleapis.com/content/v2.1/{MID}"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}"}

# 1) 免费 listing 项目状态
r = httpx.get(f"{B}/freelistingsprogram", headers=H, timeout=30)
print("freeListingsProgram:", r.status_code)
if r.status_code == 200:
    prog = r.json()
    for ds in prog.get("destinationStatuses", []):
        print(f"  region={ds.get('regionCodes')} destination="
              f"{ds.get('destination')} status={ds.get('status')}")
    for iss in prog.get("issues", [])[:5]:
        print("  issue:", iss.get("title"), "|", iss.get("severity"),
              iss.get("documentation", "")[:60])
else:
    print("  body:", r.text[:300])

# 2) 若未激活且非 DISAPPROVED → 申请 US 复核激活
statuses = [ds.get("status") for ds in r.json().get("destinationStatuses", [])] \
    if r.status_code == 200 else []
if statuses and all(s not in ("ACTIVE", "EXPIRING") for s in statuses):
    rr = httpx.post(f"{B}/freelistingsprogram/requestreview",
                    headers={**H, "Content-Type": "application/json"},
                    json={"regionCode": "US"}, timeout=30)
    print("requestreview(US):", rr.status_code, rr.text[:200])
    time.sleep(3)
    r2 = httpx.get(f"{B}/freelistingsprogram", headers=H, timeout=30)
    if r2.status_code == 200:
        print("复核后状态:",
              [ds.get("status") for ds in
               r2.json().get("destinationStatuses", [])])

# 3) feed 健康：productstatuses 分页统计
print("\n=== feed 健康（productstatuses）===")
stats = Counter()
issues = Counter()
tok, total = None, 0
while True:
    params = {"maxResults": 250}
    if tok:
        params["pageToken"] = tok
    p = httpx.get(f"{B}/productstatuses", headers=H, params=params,
                  timeout=60)
    if p.status_code != 200:
        print("productstatuses FAIL:", p.status_code, p.text[:200])
        break
    data = p.json()
    for it in data.get("resources", []):
        total += 1
        for ils in it.get("itemLevelIssues", []):
            serv = ils.get("servability", "")
            stats[serv] += 1
            if serv != "SERVED":
                issues[ils.get("title", "?")] += 1
    tok = data.get("nextPageToken")
    if not tok:
        break
print(f"SKU 总数(可见状态条目): {total}")
print("servability 分布:", dict(stats) or "全部无 issue")
for t, n in issues.most_common(10):
    print(f"  未投放原因: {t} x{n}")
