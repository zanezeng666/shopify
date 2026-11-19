"""今天的订单从哪来：Shopify 订单归因字段 + GA4 sessionSource 交叉"""
import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

ENV = {}
with open("/home/jason/shopify-admin/.env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            ENV[k.strip()] = v.strip()

BJ = timezone(timedelta(hours=8))
now_bj = datetime.now(BJ)
since = (now_bj - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _order_source(o: dict) -> str:
    """来源判定：landing_site 的 utm 优先（ChatGPT/app 内浏览器不带 referrer 时唯一线索），
    退 referring_site 域名，最后 (direct)。"""
    ls = o.get("landing_site") or ""
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(ls).query)
    u = {k: v[0] for k, v in q.items()
         if k.lower().startswith(("utm_", "gad_", "gclid", "gbraid"))}
    rs = o.get("referring_site") or ""
    rdom = urllib.parse.urlsplit(rs).netloc if rs else ""
    if "utm_source" in u:
        tag = u["utm_source"] + (f"/{u['utm_medium']}" if "utm_medium" in u else "")
        if "utm_campaign" in u:
            tag += f" ({u['utm_campaign']})"
        if "gad_source" in u or "gbraid" in u:
            tag += " [Google Ads]"
        return tag + "  ← landing_site utm"
    rq = urllib.parse.parse_qs(urllib.parse.urlsplit(rs).query)
    rads = any(k in rq for k in ("gad_source", "gclid", "gbraid", "wbraid"))
    if rads:
        cid = rq.get("gad_campaignid", [""])[0]
        return f"google-ads (campaign {cid})  ← referring_site gad/gclid 标记（结账跳转覆盖了外层 referrer）"
    if rdom and rdom not in ("www.estrybattery.com", "estrybattery.com"):
        return f"{rdom}  ← referring_site"
    if rdom:
        return f"{rdom}（自家域名跳转，无进一步归因）  ← referring_site"
    return "(direct/无归因)"

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores import StoreService

client = StoreService().get_client(1)
orders = client.request("GET", "orders.json", params={
    "status": "any", "limit": 50, "created_at_min": since,
    "fields": "id,name,created_at,total_price,financial_status,gateway,payment_names,"
              "source_name,referring_site,landing_site,note_attributes,customer,cancelled_at",
})
rows = orders.get("orders", [])
print(f"== Shopify 近48h订单（北京时间 {since} ~ {now_bj:%m-%d %H:%M}）共 {len(rows)} 单 ==")
for o in rows:
    ts = datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")).astimezone(BJ)
    cust = (o.get("customer") or {})
    na = {a["name"]: a["value"] for a in (o.get("note_attributes") or [])}
    utm = {k: v for k, v in na.items() if k.lower() in ("utm source","utm_source","utm medium","utm_medium","utm campaign","utm_campaign","gclid","referrer")}
    print(f"\n#{o['name']}  {ts:%m-%d %H:%M}  ¥{o['total_price']}  {o['financial_status']}"
          f"  gateway={o.get('gateway')}")
    print(f"  ★ 来源={_order_source(o)}")
    if o.get("cancelled_at"):
        print(f"  !! 已取消 {o['cancelled_at']}")
    print(f"  source_name={o.get('source_name')}")
    print(f"  referring_site={o.get('referring_site') or '(空=直访/无referrer)'}")
    print(f"  landing_site={o.get('landing_site') or '(空)'}")
    if utm:
        print(f"  note_attributes归因={utm}")
    print(f"  customer={cust.get('email','?')} ({cust.get('first_name','')} {cust.get('last_name','')})")

# ---- GA4 交叉：近3天 purchase 的 sessionSource ----
tok = json.load(urllib.request.urlopen(
    "https://oauth2.googleapis.com/token",
    data=urllib.parse.urlencode({
        "client_id": ENV["GOOGLE_CLIENT_ID"], "client_secret": ENV["GOOGLE_CLIENT_SECRET"],
        "refresh_token": ENV["GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token",
    }).encode(),
))["access_token"]
body = {
    "dateRanges": [{"startDate": (now_bj - timedelta(days=2)).strftime("%Y-%m-%d"),
                    "endDate": now_bj.strftime("%Y-%m-%d")}],
    "dimensions": [{"name": "date"}, {"name": "sessionSource"}, {"name": "sessionMedium"}],
    "metrics": [{"name": "eventCount"}, {"name": "eventValue"}],
    "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": "purchase"}}},
}
req = urllib.request.Request(
    "https://analyticsdata.googleapis.com/v1beta/properties/313397200:runReport",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
)
try:
    rep = json.load(urllib.request.urlopen(req))
    print(f"\n== GA4 近3天 purchase 事件按来源（注：当日数据延迟 1~3 小时，最新订单可能未入） ==")
    if rep.get("rows"):
        for row in rep["rows"]:
            d, m = row["dimensionValues"], row["metricValues"]
            print(f"  {d[0]['value']}  {d[1]['value']}/{d[2]['value']:<12} events={m[0]['value']}  value={m[1]['value']}")
    else:
        print("  (近3天无 purchase 事件——当日订单可能仍在 GA4 处理延迟窗口内)")
except urllib.error.HTTPError as e:
    print(f"GA4 {e.code}: {e.read().decode()[:300]}")
