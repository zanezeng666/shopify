# -*- coding: utf-8 -*-
"""服务器代码版本 + Shopify API 直连测试"""
import subprocess
import time


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


print("=== 服务器 settings.py shopify 字段 ===")
print(sh("grep -n 'shopify_' /home/jason/shopify-admin/src/shopify_admin/config/settings.py | head -30"))
print()
print("=== 服务器 client.py timeout/proxy/retry ===")
print(sh("grep -n -i 'timeout\\|proxy\\|retry\\|sleep' /home/jason/shopify-admin/src/shopify_admin/platforms/shopify/client.py | head -40"))
print()
print("=== 服务器 graphql.py timeout ===")
print(sh("grep -n -i 'timeout\\|proxy\\|retry\\|sleep' /home/jason/shopify-admin/src/shopify_admin/platforms/shopify/graphql.py | head -20"))

print()
print("=== Shopify API 直连测试（10s 超时） ===")
test_code = r'''
import sys, time
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
st = StoreService().list_stores(available_only=True)[0]
print("store:", st["id"], st.get("domain"), "token_head:", (st.get("access_token") or "")[:6])
import httpx
url = f"https://{st['domain']}/admin/api/2024-10/graphql.json"
q = {"query": "{ shop { name myshopifyDomain } }"}
t0 = time.time()
try:
    r = httpx.post(url, json=q, headers={"X-Shopify-Access-Token": st["access_token"]}, timeout=10.0)
    print(f"elapsed={time.time()-t0:.2f}s status={r.status_code}")
    print("body:", r.text[:300])
except Exception as e:
    print(f"elapsed={time.time()-t0:.2f}s EXC {type(e).__name__}: {e}")
'''
r = subprocess.run(
    ["/home/jason/shopify-admin/.venv/bin/python", "-c", test_code],
    capture_output=True, text=True, cwd="/home/jason/shopify-admin",
    timeout=60,
)
print(r.stdout or r.stderr)
