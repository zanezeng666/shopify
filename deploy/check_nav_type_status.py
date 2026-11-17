# -*- coding: utf-8 -*-
"""核实导航挂载的各 product_type 线上 ACTIVE/DRAFT 状态。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

TYPES = [
    "Mobile SmartPhone Battery", "Tablet Battery", "Smartwatch Battery",
    "Notebook,Laptop Battery", "UMPC/Netbook Battery", "Keyboard,Mouse Battery",
    "PLC Battery", "PDA/Pocket PC Battery",
    "Camera Battery", "Drones Battery", "Battery Grip Battery",
    "Home Security Camera Battery", "Thermal Camera Battery",
    "Speaker Battery", "GPS/Navigator Battery", "Media Player Battery",
    "Game Console Battery", "Ebook/EReader Battery",
    "Two-Way Radio Battery", "Cordless Phone Battery",
    "Wireless Headset Battery", "Hotspot Battery", "BabyPhone Battery",
    "Satellite Phone Battery",
    "Power Tools Battery", "Equipment,Survey,Test Battery",
    "Barcode Scanner Battery", "Payment Terminal Battery",
    "Microscope Battery",
    "Vacuum Battery", "Lawn Mowers Battery", "Dog Collar Battery",
    "Shaver Battery", "Toothbrush Battery", "Electronic Magnifier Battery",
    "Medical Battery",
]


def count(**kw):
    return cl.request("GET", "products/count.json", params=kw).get("count")


print(f"{'product_type':34} {'ACTIVE':>7} {'TOTAL':>7}  判定")
for t in TYPES:
    try:
        act = count(product_type=t, status="active")
        tot = count(product_type=t)
        verdict = "OK 挂载" if act > 0 else "★全DRAFT 必撤"
        print(f"{t:34} {act:>7} {tot:>7}  {verdict}")
    except Exception as e:
        print(f"{t:34} ERR {str(e)[:60]}")
