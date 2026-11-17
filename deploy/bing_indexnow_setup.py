# -*- coding: utf-8 -*-
"""Bing 收录加速：IndexNow 部署与全量提交。
流程：生成 key → 主题 assets 放 key 文件（Shopify 无法放根目录，用 keyLocation 参数指向 CDN）
→ 验证 key URL → 抓 sitemap 全量 URL → 小样测试链路 → 分批全量提交。
状态落盘 deploy/idxnow_state.json 供每日增量 job 复用。
"""
import json
import re
import secrets
import sys
import time

import httpx

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

TID = 190031036660
HOST = "www.estrybattery.com"
STATE = "/home/jason/shopify-admin/deploy/idxnow_state.json"
API = "https://api.indexnow.org/indexnow"
UA = {"User-Agent": "Mozilla/5.0 (compatible; EstryIndexNow/1.0)"}

c = ShopifyRest(StoreService().get_client(1)).client


def load_key():
    try:
        with open(STATE) as f:
            k = json.load(f).get("key")
            if k and re.fullmatch(r"[a-f0-9]{32}", k):
                return k
    except Exception:
        pass
    return secrets.token_hex(16)


key = load_key()
asset_key = f"assets/{key}.txt"

# ---------- 1. 上传 key 文件到主题 assets ----------
res = c.request("PUT", f"themes/{TID}/assets.json",
                json_body={"asset": {"key": asset_key, "value": key}})
info = res.get("asset", {})
key_url = info.get("public_url", "")
print(f"key={key}")
print(f"asset public_url={key_url}")
with open(STATE, "w") as f:
    json.dump({"key": key, "key_url": key_url, "asset_key": asset_key}, f)

# ---------- 2. 等 CDN 传播并验证 key URL ----------
verified = False
for i in range(8):
    time.sleep(5 if i else 2)
    try:
        r = httpx.get(key_url, headers=UA, timeout=30, follow_redirects=True)
        if r.status_code == 200 and r.text.strip() == key:
            verified = True
            break
        print(f"  key url 探测 {i+1}: code={r.status_code} body={r.text[:40]!r}")
    except Exception as e:
        print(f"  key url 探测 {i+1}: {e}")
if not verified:
    print("!! key URL 验证失败，IndexNow 提交可能被拒，继续尝试小样测试")
else:
    print(f"key URL 验证通过: {key_url}")

# ---------- 3. 抓取 sitemap 全量 URL ----------
idx = httpx.get(f"https://{HOST}/sitemap.xml", headers=UA, timeout=60,
                follow_redirects=True)
shards = list(dict.fromkeys(
    s for s in re.findall(r"<loc>(.*?)</loc>", idx.text) if "sitemap" in s))
print(f"\nsitemap 分片 {len(shards)} 个（去重后）")

urls = []
for s in shards:
    for attempt in range(3):
        try:
            r = httpx.get(s, headers=UA, timeout=90, follow_redirects=True)
            locs = re.findall(r"<loc>(.*?)</loc>", r.text)
            tag = s.split("sitemap_")[-1].split(".xml")[0].split("?")[0]
            print(f"  {tag}: {len(locs)} URL")
            urls.extend(locs)
            break
        except Exception as e:
            print(f"  分片失败 {s} 第{attempt+1}次: {e}")
            time.sleep(3)
urls = [u for u in urls if u.startswith("https://")]
urls = sorted(set(urls))
print(f"\nURL 总量 {len(urls)}（去重后）")

# ---------- 4. 小样测试（key 经根路径 redirect 提供）----------
probe = httpx.get(API, params={"url": f"https://{HOST}/", "key": key},
                  headers=UA, timeout=60, follow_redirects=True)
print(f"\n小样测试: HTTP {probe.status_code} {probe.text[:80]!r}")
if probe.status_code not in (200, 202):
    print("!! 链路未通，停止全量提交；常见原因= key 文件路径/内容不符合要求")
    sys.exit(1)

# ---------- 5. 分批全量提交 ----------
B = 8000
total_ok = 0
for i in range(0, len(urls), B):
    batch = urls[i:i + B]
    r = httpx.post(API, headers={**UA, "Content-Type": "application/json; charset=utf-8"},
                   json={"host": HOST, "key": key,
                         "urlList": batch}, timeout=120)
    print(f"批 {i//B+1}: {len(batch)} URL -> HTTP {r.status_code} {r.text[:60]!r}")
    if r.status_code in (200, 202):
        total_ok += len(batch)
    time.sleep(2)

print(f"\n=== IndexNow 提交完成: {total_ok}/{len(urls)} URL 被接受 ===")
print(f"状态文件: {STATE}")
