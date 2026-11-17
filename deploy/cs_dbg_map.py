# -*- coding: utf-8 -*-
"""CS-WB710MD 的 Shopify 产品id + 图(GraphQL验证线上真实存在)。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from shopify_admin.core.database import get_engine  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

load_dotenv("/home/jason/shopify-admin/.env")
with get_engine().connect() as m:
    rows = m.execute(text(r"""
        SELECT p.shopify_product_id, p.title, p.status
        FROM products p JOIN product_variants pv ON pv.product_id=p.id
        WHERE pv.store_id=1 AND pv.sku LIKE 'CS-WB710MD\_%'
        GROUP BY 1,2,3""")).fetchall()
    for r in rows:
        print(f"{r[0]} [{r[2]}] {str(r[1])[:60]}")

if rows:
    pid = rows[0][0]
    cl = ShopifyRest(StoreService().get_client(1)).client
    Q = """
    query($id: ID!){
      product(id:$id){
        id status title
        featuredImage { url }
        images(first: 2) { nodes { url } }
      }
    }"""
    p = cl.graphql(Q, {"id": f"gid://shopify/Product/{pid}"}).get("product")
    if p:
        print(f"\n线上验证: [{p['status']}] {p['title'][:56]}")
        print(f"  featured: {str(p['featuredImage'] and p['featuredImage']['url'])[:100]}")
    else:
        print("\n线上验证: 产品不存在!")
