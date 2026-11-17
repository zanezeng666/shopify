# -*- coding: utf-8 -*-
"""验证样例产品 v2.1 描述上线。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

b = (ShopifyRest(StoreService().get_client(1))
     .product_by_handle("battery-for-delonghi-colombina-evo-xml510-as00000910")
     .get("body_html") or "")
print("18px 标题:", "font-size:18px" in b)
print("品牌绿边框:", "#00A651" in b)
print("14px 辅助文字:", b.count("font-size:14px"), "处")
print("15px 定义句:", "font-size:15px" in b)
print("残留旧 16px:", b.count("font-size:16px"), "处")
print("残留旧 13px:", b.count("font-size:13px"), "处（徽章 13px 属正常）")
