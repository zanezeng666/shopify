# -*- coding: utf-8 -*-
"""拉当前主导航结构，定位 Phone/Laptop/Camera 组与死入口。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

menus = cl.request("GET", "menus.json").get("menus", [])
main = next(m for m in menus if "main" in m["handle"].lower())
items = cl.request("GET", f"menus/{main['id']}/items.json").get("items", [])

def walk(items, depth=0):
    for it in items:
        print("  " * depth + f"- {it['title']}  ->  {it.get('url','')}")
        if it.get("items"):
            walk(it["items"], depth + 1)

print(f"主菜单 handle={main['handle']} id={main['id']} 顶层 {len(items)} 项")
walk(items)
with open("/tmp/mainmenu_now.json", "w") as f:
    json.dump(items, f, indent=1)
print("\n已存 /tmp/mainmenu_now.json")
