# -*- coding: utf-8 -*-
"""Shopify API 连通性双路测试：裸 httpx vs 项目 client.graphql"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
import httpx

from shopify_admin.services.stores.service import StoreService

svc = StoreService()
client = svc.get_client(1)
tok = client.creds.api_key
dom = client.creds.domain
url = f"https://{dom}/admin/api/2024-10/graphql.json"
print(f"domain={dom} token_head={tok[:6]}...")

# 路 1：裸 httpx，10s 超时
q = {"query": "{ shop { name myshopifyDomain } }"}
t0 = time.time()
try:
    r = httpx.post(url, json=q, headers={"X-Shopify-Access-Token": tok}, timeout=10.0)
    print(f"[raw httpx] elapsed={time.time()-t0:.2f}s status={r.status_code} body={r.text[:200]}")
except Exception as e:
    print(f"[raw httpx] elapsed={time.time()-t0:.2f}s EXC {type(e).__name__}: {e}")

# 路 2：项目 client（30s 超时+静默重试），最多观察 90s
t0 = time.time()
try:
    data = client.graphql("{ shop { name } }")
    print(f"[client] elapsed={time.time()-t0:.2f}s data={data}")
except Exception as e:
    print(f"[client] elapsed={time.time()-t0:.2f}s EXC {type(e).__name__}: {str(e)[:300]}")

# 路 3：一个真实 bulk price mutation 形态（10 变体），测大 payload
t0 = time.time()
try:
    mut = """
    mutation bulkPrice($products: [ProductSetInput!]!) { productSet(products: $products) { userErrors { message } } }
    """
    # 不真发，只构造——跳过
    print("[mut] skipped")
except Exception as e:
    print("mut EXC", e)
