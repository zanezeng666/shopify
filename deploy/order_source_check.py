"""复查 24452460184：① GA4 会话级 Ads 账户号/campaign id ② 主账户 change_event ③ 全账户全量 campaign 精确比对。只读。"""
import os

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

import httpx
from google.ads.googleads.client import GoogleAdsClient

TARGET = 24452460184
GA4 = "313397200"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

# --- ① GA4 会话级 Google Ads 归因维度 ---
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
URL = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}:runReport"


def rep(body, tag):
    j = httpx.post(URL, headers=H, json=body, timeout=60).json()
    print(f"\n[{tag}]" if j.get("rows") else f"[{tag}] 无: {j.get('err', j.get('rowCount', 0))}")
    for row in j.get("rows") or []:
        vals = [d["value"] for d in row["dimensionValues"]] + [m["value"] for m in row["metricValues"]]
        print("  " + " | ".join(vals))


for dims in ([{"name": "sessionGoogleAdsAccountID"}, {"name": "sessionCampaignId"}],
             [{"name": "sessionCampaignId"}, {"name": "sessionCampaign"}]):
    try:
        rep({"dateRanges": [{"startDate": "2026-11-14", "endDate": "2026-11-18"}],
             "dimensions": dims,
             "metrics": [{"name": "sessions"}],
             "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
             "limit": 25}, f"GA4 {'+'.join(d['name'] for d in dims)}")
    except Exception as e:
        print(e)

# --- ② 主账户 change_event：30 天内 CAMPAIGN 变更，grep 目标 id ---
try:
    r = gas.search(customer_id="7059800494", query=(
        "SELECT change_event.change_date_time, change_event.change_resource_name, "
        "change_event.change_status_type, change_event.user_email, change_event.client_type "
        "FROM change_event WHERE change_event.change_resource_type = 'CAMPAIGN' "
        "AND change_event.change_date_time >= '2026-10-19 00:00:00' LIMIT 10000"))
    hits, total = [], 0
    for row in r:
        total += 1
        ce = row.change_event
        if str(TARGET) in ce.change_resource_name:
            hits.append(f"{ce.change_date_time} {ce.change_resource_name.split('/')[-1]} "
                        f"{ce.change_status_type.name} by {ce.user_email} ({ce.client_type.name})")
    print(f"\n[主账户 change_event] 30天 CAMPAIGN 变更 {total} 条，目标 id 命中 {len(hits)} 条")
    for h in hits[:20]:
        print(f"  ★ {h}")
    if not hits and total:
        # 顺带列出近 7 天新建/删除的 campaign 变更（可能 id 变体）
        print("  （无命中；列出最近 10 条 CAMPAIGN 变更样本）")
        for row in list(r)[:0]:
            pass
except Exception as e:
    print(f"[change_event] 失败: {str(e)[:300]}")

# --- ③ 三个账户全量 campaign 精确比对 ---
for cid in ["7059800494", "1651348739", "2214926660"]:
    try:
        r2 = gas.search(customer_id=cid, query=(
            "SELECT campaign.id, campaign.name, campaign.status, "
            "campaign.advertising_channel_type FROM campaign"))
        rows = [(c.id, c.name, c.status.name, c.advertising_channel_type.name)
                for c in (row.campaign for row in r2)]
        hit = [x for x in rows if x[0] == TARGET]
        print(f"\n[账户 {cid}] 全量 campaign {len(rows)} 个，目标命中: {hit if hit else '无'}")
        if cid != "7059800494" and rows:
            for x in rows[:10]:
                print(f"  {x}")
        if cid == "7059800494":
            near = [x for x in rows if abs(x[0] - TARGET) < 20000000]
            print(f"  id ±2000万 邻近: {near}")
    except Exception as e:
        print(f"[账户 {cid}] 失败: {str(e)[:200]}")
