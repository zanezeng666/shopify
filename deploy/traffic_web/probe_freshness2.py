# -*- coding: utf-8 -*-
"""round2：realtime 层形态确认——无维度聚合/页面维度/事件组合/inList/多维组合。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
GA4 = "313397200"


def _tok() -> str:
    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


AT = _tok()


def call(ep: str, body: dict):
    r = httpx.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}:{ep}",
        headers={"Authorization": f"Bearer {AT}",
                 "Content-Type": "application/json"},
        json=body, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:150]}")
    return r.json()


def t(name, body, show=3):
    try:
        j = call("runRealtimeReport", body)
        rows = j.get("rows", [])
        head = ["|".join(x["value"] for x in r.get("dimensionValues", [])) +
                " -> " + ",".join(m["value"] for m in r["metricValues"])
                for r in rows[:show]]
        print(f"OK   {name} rows={len(rows)} {' ; '.join(head)}")
        return True
    except RuntimeError as e:
        print(f"FAIL {name}: {e}")
        return False


# 1) 无维度聚合（去掉 sessions 后再试）
t("无维度聚合 4 指标", {"metrics": [{"name": "activeUsers"},
                                   {"name": "eventCount"},
                                   {"name": "screenPageViews"},
                                   {"name": "keyEvents"}], "limit": 10})

# 2) 页面/屏幕维度
for d in ["unifiedScreenName", "pagePath", "pageScreen", "unifiedPageScreen"]:
    t(f"dim {d}", {"dimensions": [{"name": d}],
                   "metrics": [{"name": "activeUsers"},
                               {"name": "screenPageViews"}], "limit": 5})

# 3) 首话来源类（当日新客归因近似）
for d in ["firstUserSource", "firstUserMedium", "firstUserSourceMedium",
          "firstUserDefaultChannelGroup"]:
    t(f"dim {d}", {"dimensions": [{"name": d}],
                   "metrics": [{"name": "activeUsers"}], "limit": 5})

# 4) 事件组合
t("eventName+keyEvents", {"dimensions": [{"name": "eventName"}],
                          "metrics": [{"name": "keyEvents"}], "limit": 5})
t("eventName+eventCount", {"dimensions": [{"name": "eventName"}],
                           "metrics": [{"name": "eventCount"}], "limit": 5})
t("eventName inList 过滤", {
    "dimensions": [{"name": "eventName"}],
    "metrics": [{"name": "eventCount"}],
    "dimensionFilter": {"filter": {"fieldName": "eventName",
                                   "inListFilter": {"values": [
                                       "add_to_cart", "begin_checkout",
                                       "purchase", "generate_lead"]}}},
    "limit": 10})

# 5) 多维组合
t("country+deviceCategory", {"dimensions": [{"name": "country"},
                                            {"name": "deviceCategory"}],
                             "metrics": [{"name": "activeUsers"},
                                         {"name": "keyEvents"}], "limit": 5})
t("country+city", {"dimensions": [{"name": "country"}, {"name": "city"}],
                   "metrics": [{"name": "activeUsers"}], "limit": 5})
