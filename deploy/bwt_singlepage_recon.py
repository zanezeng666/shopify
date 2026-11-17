# -*- coding: utf-8 -*-
"""修复前侦查：header.liquid h1 段 + all 集合 ID + title job 终态。只读。"""
import json
import subprocess
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

cl = ShopifyRest(StoreService().get_client(1)).client

# 1. header.liquid 的 h1 相关段
a = cl.request("GET", f"themes/190031036660/assets.json",
               params={"asset[key]": "sections/header.liquid"})
src = a["asset"]["value"]
i = src.find("page_type == 'index'")
print("== header.liquid h1 上下文 ==")
print(src[max(0, i - 200): i + 700])

# 2. all 集合
c = cl._client.get("collections/all.json", auth=cl._auth)
print(f"\n== collections/all: HTTP {c.status_code} ==")
try:
    print(json.dumps(c.json(), ensure_ascii=False)[:300])
except Exception:
    print(c.text[:200])

# 3. title job
r = subprocess.run(["pgrep", "-af", "bwt_title_fix"], capture_output=True,
                   text=True)
print(f"\n== title job 进程: {r.stdout or '已结束'}")
done = json.load(open("/home/jason/shopify-admin/deploy/bwt_title_fix_done.json"))
print(f"done: {len(done)}")
log = subprocess.run(["tail", "-n", "3",
                      "/home/jason/shopify-admin/logs/bwt_title_fix.log"],
                     capture_output=True, text=True)
print(log.stdout)
