"""终局验证：订单 #2241 是否 PMax(24441391608) 带来。①产品级点击实锤 ②24452460184 三表身份比对 ③PMax 小时曲线。只读。"""
import os

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")
CID, TARGET = "7059800494", 24452460184

# --- ① PMax 产品级点击（近 4 天）---
print("[① shopping_performance_view PMax 产品点击 11-15~18]")
try:
    r = gas.search(customer_id=CID, query=(
        "SELECT segments.product_item_id, segments.product_title, segments.date, "
        "metrics.clicks, metrics.impressions, metrics.cost_micros, metrics.conversions "
        "FROM shopping_performance_view "
        "WHERE segments.date BETWEEN '2026-11-15' AND '2026-11-18' "
        "AND campaign.id = 24441391608 ORDER BY metrics.clicks DESC LIMIT 100"))
    rows = [(row.segments.product_item_id or "?", row.segments.product_title or "?",
             row.segments.date, row.metrics.clicks, row.metrics.impressions,
             row.metrics.cost_micros / 1e6, row.metrics.conversions) for row in r]
    print(f"  产品数 {len(rows)}，点击 Top（含 kangaroo 全列）：")
    hits = [x for x in rows if any(k in (x[0] + x[1]).lower() for k in ("kangaroo", "joey", "zen"))]
    for x in (hits + [y for y in rows if y not in hits][:12]):
        star = " ★" if x in hits else ""
        print(f"  {x[3]:>3}clk {x[5]:>6.2f}CNY {x[2]} | {x[0][:28]:<28} | {x[1][:44]}{star}")
except Exception as e:
    print(f"  失败: {str(e)[:200]}")

# --- ② 24452460184 身份：asset_group / ad_group / campaign+PMax asset group 比对 ---
print(f"\n[② 目标 {TARGET} 三表身份比对（PMax campaign 内）]")
for label, q in (
    ("asset_group", "SELECT asset_group.id, asset_group.name FROM asset_group WHERE campaign.id = 24441391608"),
    ("ad_group", "SELECT ad_group.id, ad_group.name, ad_group.status FROM ad_group WHERE campaign.id = 24441391608"),
    ("全部 asset_group", "SELECT asset_group.id, asset_group.name, campaign.id FROM asset_group"),
):
    try:
        r2 = gas.search(customer_id=CID, query=q)
        found = False
        for row in r2:
            obj = row.asset_group if label.startswith("asset") else row.ad_group
            mark = "★命中" if obj.id == TARGET else ""
            if mark or label != "全部 asset_group":
                print(f"  [{label}] {obj.id} | {obj.name} {mark}")
            if mark:
                found = True
        if not found and label != "全部 asset_group":
            print(f"  [{label}] 无命中")
    except Exception as e:
        print(f"  [{label}] 失败: {str(e)[:120]}")

# --- ③ PMax 小时曲线（对照下单时刻 北京 11-18 06:28）---
print("\n[③ PMax 小时级点击/花费 11-17~18]")
try:
    r3 = gas.search(customer_id=CID, query=(
        "SELECT segments.date, segments.hour, metrics.clicks, metrics.impressions, metrics.cost_micros "
        "FROM campaign WHERE campaign.id = 24441391608 "
        "AND segments.date BETWEEN '2026-11-17' AND '2026-11-18' ORDER BY segments.date, segments.hour"))
    for row in r3:
        if row.metrics.clicks > 0 or row.segments.hour in (5, 6, 7):
            print(f"  {row.segments.date} {row.segments.hour:>2}时 | {row.metrics.clicks:>3}clk "
                  f"{row.metrics.impressions:>5}imp {row.metrics.cost_micros/1e6:>7.2f}CNY")
except Exception as e:
    print(f"  失败: {str(e)[:160]}")
