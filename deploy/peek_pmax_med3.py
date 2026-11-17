# -*- coding: utf-8 -*-
"""PMax Medical Estry 诊断 v4：
D) v26 client 查树节点 caseValue（fix10 同款查询）
F) 镜像库 product_type 分布（SHOPIFY_DB_*）
"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
q = (
    "SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.type, "
    "asset_group_listing_group_filter.listing_source, "
    "asset_group_listing_group_filter.case_value.product_type.value, "
    "asset_group_listing_group_filter.case_value.product_type.level "
    "FROM asset_group_listing_group_filter "
    "WHERE campaign.id = 24441391608"
)
print("=" * 20, "D) 树节点 caseValue (v26 client)", "=" * 20)
for r in gas.search(customer_id=CID, query=q):
    f = r.asset_group_listing_group_filter
    print(f"- id={f.id} type={f.type_.name} ptype="
          f"{f.case_value.product_type.value!r} "
          f"level={f.case_value.product_type.level}")

print("\n" + "=" * 20, "F) 镜像库 product_type 分布", "=" * 20)
import pymysql  # noqa: E402

conn = pymysql.connect(
    host=os.environ["SHOPIFY_DB_HOST"],
    port=int(os.environ.get("SHOPIFY_DB_PORT", "63698")),
    user=os.environ["SHOPIFY_DB_USER"],
    password=os.environ["SHOPIFY_DB_PASSWORD"],
    database=os.environ.get("SHOPIFY_DB_NAME", "shopify_admin"),
    charset="utf8mb4")
cur = conn.cursor()
cur.execute("SELECT product_type, COUNT(*) FROM products "
            "GROUP BY product_type ORDER BY 2 DESC LIMIT 15")
print("全部类型 TOP15:")
for t, n in cur.fetchall():
    mark = "   <-- 树的筛选值" if t == "Medical Battery" else ""
    print(f"- {t!r}: {n}{mark}")
cur.execute("SELECT product_type, COUNT(*) FROM products "
            "WHERE product_type LIKE %s GROUP BY product_type "
            "ORDER BY 2 DESC", ("%Medical%",))
print("\n含 Medical 的类型:")
for t, n in cur.fetchall():
    print(f"- {t!r}: {n}")
conn.close()
