# -*- coding: utf-8 -*-
"""结账漏斗诊断：近 7 天 GA4 电商事件链计数（按天/按国家/按用户数）。
漏斗: view_item → add_to_cart → begin_checkout → add_shipping_info
      → add_payment_info → purchase"""
import datetime as dt
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
GA4 = "313397200"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}

FUNNEL = ["view_item", "add_to_cart", "begin_checkout",
          "add_shipping_info", "add_payment_info", "purchase"]


def runreport(body):
    r = httpx.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}"
        ":runReport", headers=H, json=body, timeout=60)
    return r.json() if r.status_code == 200 else {"err": r.text[:300]}


start = (dt.date.today() - dt.timedelta(days=8)).isoformat()
end = (dt.date.today() - dt.timedelta(days=1)).isoformat()
print(f"=== 结账漏斗 {start} ~ {end} ===")

# 1) 按天×事件：eventCount + totalUsers
j = runreport({
    "dateRanges": [{"startDate": start, "endDate": end}],
    "dimensions": [{"name": "date"}, {"name": "eventName"}],
    "metrics": [{"name": "eventCount"}, {"name": "totalUsers"}],
    "dimensionFilter": {"filter": {
        "fieldName": "eventName",
        "inListFilter": {"values": FUNNEL}}},
    "orderBys": [{"dimension": {"dimensionName": "date"}}]})
if "rows" in j:
    byday = {}
    for row in j["rows"]:
        d, ev = row["dimensionValues"][0]["value"], row["dimensionValues"][1]["value"]
        byday.setdefault(d, {})[ev] = (
            row["metricValues"][0]["value"], row["metricValues"][1]["value"])
    hdr = "date       " + "".join(f"{e[:14]:>16}" for e in FUNNEL)
    print(hdr)
    for d in sorted(byday):
        cells = []
        for e in FUNNEL:
            c, u = byday[d].get(e, ("0", "0"))
            cells.append(f"{c}/{u:>6}"[:16].rjust(16))
        print(d + " " + "".join(cells))
    print("(格式: 事件数/用户数)")
else:
    print("按天查询失败:", j.get("err", j))

# 2) begin_checkout 之后的深度流失：按国家
print("\n=== begin_checkout 用户国家分布（7天）===")
j2 = runreport({
    "dateRanges": [{"startDate": start, "endDate": end}],
    "dimensions": [{"name": "country"}],
    "metrics": [{"name": "eventCount"}, {"name": "totalUsers"}],
    "dimensionFilter": {"filter": {
        "fieldName": "eventName",
        "inListFilter": {"values": FUNNEL}}},
    "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
    "limit": 20})
# country 全事件矩阵
if "rows" in j2:
    # 需要每国每事件 → 重新查三维
    j3 = runreport({
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": "country"}, {"name": "eventName"}],
        "metrics": [{"name": "eventCount"}, {"name": "totalUsers"}],
        "dimensionFilter": {"filter": {
            "fieldName": "eventName",
            "inListFilter": {"values": FUNNEL}}}})
    mat = {}
    for row in j3.get("rows", []):
        c, ev = row["dimensionValues"][0]["value"], row["dimensionValues"][1]["value"]
        mat.setdefault(c, {})[ev] = (
            row["metricValues"][0]["value"], row["metricValues"][1]["value"])
    for c, d in sorted(mat.items(),
                       key=lambda kv: -int(kv[1].get("begin_checkout", ("0",))[0])):
        line = f"  {c:<18}"
        for e in FUNNEL:
            line += f" {d.get(e, ('0',))[0]:>5}"
        print(line)
    print("  " + " " * 18 + "".join(f"{e[:5]:>6}" for e in FUNNEL))
else:
    print("国家查询失败:", j2.get("err", j2))

# 3) 会话维度：进过 begin_checkout 的会话是否曾到 add_shipping_info
print("\n=== begin_checkout 会话流向（sessionCampaignGroup 不可用，改用 pagePath 简查）===")
j4 = runreport({
    "dateRanges": [{"startDate": start, "endDate": end}],
    "dimensions": [{"name": "eventName"}],
    "metrics": [{"name": "eventCount"}, {"name": "totalUsers"},
                {"name": "sessions"}],
    "dimensionFilter": {"filter": {
        "fieldName": "eventName",
        "inListFilter": {"values": FUNNEL + ["generate_lead"]}}}})
if "rows" in j4:
    for row in j4["rows"]:
        ev = row["dimensionValues"][0]["value"]
        m = row["metricValues"]
        print(f"  {ev:<20} events={m[0]['value']:>4} users={m[1]['value']:>4} "
              f"sessions={m[2]['value']:>4}")
else:
    print("流向查询失败:", j4.get("err", j4))
