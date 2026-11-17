# -*- coding: utf-8 -*-
"""P0-1 转化跟踪闭环验证：
A) Ads 账户转化动作清单（类型/状态/类目/增强型转化开关）
B) 近14天账户与campaign级转化回流数据
C) 店面 gtag 注入检查（GA4 ID / AW ID / conversion label）
"""
import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

CID = "7059800494"
TOK = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {TOK}", "developer-token": "unused",
     "login-customer-id": CID}


def gaql(query):
    r = httpx.post(
        f"https://googleads.googleapis.com/v25/customers/{CID}/googleAds:searchStream",
        headers=H, json={"query": query}, timeout=90)
    if r.status_code != 200:
        print("GAQL error:", r.status_code, r.text[:400])
        return []
    return [row for batch in r.json() for row in batch.get("results", [])]


print("=" * 20, "A) 转化动作清单", "=" * 20)
BASE = """
    SELECT conversion_action.resource_name, conversion_action.name,
      conversion_action.type, conversion_action.status,
      conversion_action.category
    FROM conversion_action"""
rows = gaql(BASE)
if not rows:
    raise SystemExit("转化动作基础查询失败")
# 渐进式补字段：失败不影响主体
extra = {}
for field, key in (
        ("conversion_action.count_type", "countType"),
        ("conversion_action.primary_for_goal", "primaryForGoal"),
        ("conversion_action.enhanced_conversions_for_web_enabled",
         "enhancedConversionsForWebEnabled"),
        ("conversion_action.attribution_model", "attributionModel"),
        ("conversion_action.value_settings", "valueSettings")):
    r2 = gaql(f"SELECT {field} FROM conversion_action "
              f"LIMIT 1")
    if r2 and key in r2[0]["conversionAction"]:
        extra[field] = key
    else:
        print(f"(字段不可用: {field})")
if extra:
    sel = ("conversion_action.resource_name, conversion_action.name, "
           "conversion_action.type, conversion_action.status, "
           "conversion_action.category, " + ", ".join(extra))
    rows = gaql(f"SELECT {sel} FROM conversion_action")
ga_imported = web_actions = 0
for r in sorted(rows, key=lambda x: x["conversionAction"]["name"]):
    a = r["conversionAction"]
    t = a.get("type", "?")
    if t == "GOOGLE_ANALYTICS_4":
        ga_imported += 1
    if t in ("WEBPAGE", "GOOGLE_ANALYTICS_4", "FIREBASE",
             "THIRD_PARTY_ANALYTICS"):
        web_actions += 1
    print(f"- {a['name']!r} | type={t} | {a.get('status')} | "
          f"cat={a.get('category')}"
          + (f" | primary={a.get('primaryForGoal')}" if "primaryForGoal" in a else "")
          + (f" | enh_web={a.get('enhancedConversionsForWebEnabled')}" if "enhancedConversionsForWebEnabled" in a else "")
          + (f" | value={a.get('valueSettings')}" if "valueSettings" in a else ""))
print(f"\n合计 {len(rows)} 个转化动作（GA4导入 {ga_imported} / 网站类 {web_actions}）")

print("=" * 20, "B) 近14天转化回流", "=" * 20)
rows = gaql("""
    SELECT campaign.name, metrics.clicks, metrics.conversions,
      metrics.conversions_value, metrics.cost_micros
    FROM campaign WHERE segments.date DURING LAST_14_DAYS
      AND campaign.status != 'REMOVED'""")
tot = {"clicks": 0, "conv": 0.0, "val": 0.0, "cost": 0}
for r in rows:
    m = r["metrics"]
    tot["clicks"] += int(m.get("clicks", 0))
    tot["conv"] += float(m.get("conversions", 0))
    tot["val"] += float(m.get("conversionsValue", 0))
    tot["cost"] += int(m.get("costMicros", 0))
active = [r for r in rows
          if float(r["metrics"].get("conversions", 0)) > 0]
print(f"账户近14天: 点击={tot['clicks']} 转化={tot['conv']} "
      f"转化价值={tot['val']:.2f} 花费={tot['cost']/1e6:.2f}")
print(f"有转化的 campaign: {len(active)}")
for r in sorted(active, key=lambda x: -float(x["metrics"]["conversions"]))[:10]:
    m = r["metrics"]
    print(f"  - {r['campaign']['name']}: conv={m['conversions']} "
          f"val={m.get('conversionsValue', 0)} clicks={m.get('clicks')}")

print("\n--- PMax 转化按动作细分(近14天) ---")
rows = gaql("""
    SELECT conversion_action.name, metrics.conversions,
      metrics.conversions_value, metrics.cost_micros
    FROM campaign WHERE segments.date DURING LAST_14_DAYS
      AND campaign.status != 'REMOVED'
      AND metrics.conversions > 0""")
seen = {}
for r in rows:
    nm = r["conversionAction"]["name"]
    d = seen.setdefault(nm, [0, 0.0])
    d[0] += float(r["metrics"]["conversions"])
    d[1] += float(r["metrics"].get("conversionsValue", 0))
for nm, (c, v) in sorted(seen.items(), key=lambda kv: -kv[1][0]):
    print(f"  - {nm!r}: conv={c:g} value={v:.2f}")

print("=" * 20, "C) 店面 gtag 注入", "=" * 20)
try:
    resp = httpx.get("https://estrybattery.com/", timeout=30,
                     follow_redirects=True,
                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; "
                               "Win64; x64) AppleWebKit/537.36 (KHTML, like "
                               "Gecko) Chrome/130.0 Safari/537.36",
                              "Accept-Language": "en-US,en;q=0.9"})
    html = resp.text
    print("storefront:", resp.status_code, f"{len(html)}b")
    print("GA4 ids:", sorted(set(re.findall(r"G-[A-Z0-9]{6,12}", html))))
    print("AW ids:", sorted(set(re.findall(r"AW-\d{8,12}", html))))
    print("gtag.js:", "googletagmanager" in html)
    labels = sorted(set(re.findall(r"send_to['\"]?\s*:\s*['\"]([^'\"]+)['\"]",
                                   html)))
    print("send_to labels:", labels[:12])
    for pat in ("gtag('config'", 'gtag("config"', "gtag('event'",
                'gtag("event"'):
        if pat in html:
            print("found:", pat)
except Exception as ex:  # noqa: BLE001
    print("storefront check fail:", ex)
