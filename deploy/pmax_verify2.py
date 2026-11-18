"""shopping_performance_view 最小查询：PMax 产品级点击。只读。"""
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
CID = "7059800494"

attempts = [
    ("v1 基础", "SELECT segments.product_item_id, metrics.clicks, metrics.cost_micros "
                "FROM shopping_performance_view WHERE segments.date = '2026-11-17' "
                "AND campaign.id = 24441391608 LIMIT 60"),
    ("v2 无campaign过滤", "SELECT segments.product_item_id, metrics.clicks, metrics.cost_micros "
                        "FROM shopping_performance_view WHERE segments.date BETWEEN "
                        "'2026-11-15' AND '2026-11-18' LIMIT 60"),
    ("v3 商品视图", "SELECT product_view.id, product_view.title, product_view.item_id "
                 "FROM product_view LIMIT 5"),
]
for tag, q in attempts:
    try:
        r = gas.search(customer_id=CID, query=q)
        n = 0
        for row in r:
            n += 1
            if n <= 45:
                if hasattr(row, "product_view") and row.product_view:
                    print(f"  [{tag}] {row.product_view.item_id} | {row.product_view.title[:50]}")
                else:
                    print(f"  [{tag}] {row.segments.product_item_id} | "
                          f"{row.metrics.clicks}clk {row.metrics.cost_micros/1e6:.2f}CNY")
        print(f"  [{tag}] 共 {n} 行\n")
        if n:
            break
    except Exception as e:
        print(f"  [{tag}] 失败: {str(e)[:130]}\n")
