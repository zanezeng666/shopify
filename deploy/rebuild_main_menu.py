# -*- coding: utf-8 -*-
"""main-menu 重构 v2：MenuItemCreateInput 正确契约。

- 二级：type=COLLECTION + resourceId=collection gid（URL 变更自动跟随）
- 父级组：type=HTTP（无 url，纯展开容器）；Medical/Shop All：直链
- 原菜单已备份 deploy/backup_main_menu.json
"""
import json
import sys

import httpx

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
creds = cl.creds
headers = {"Accept": "application/json", "Content-Type": "application/json"}
if getattr(cl, "_token", None):
    headers["X-Shopify-Access-Token"] = cl._token
hc = httpx.Client(base_url=f"https://{creds.domain}/admin/api/2025-01/",
                  timeout=60, headers=headers, auth=cl._auth)

MENU_ID = "gid://shopify/Menu/59300577380"
BASE = "https://estrybattery.com"

# collection handle -> REST id（来自全量映射探测）
COLS = {
    "mobile-smartphone-battery": 159760023652, "tablet-battery": 159916785764,
    "smartwatch-battery": 159918588004, "notebook-laptop-battery": 159760285796,
    "umpc-netbook-battery": 159760810084, "keyboard-mouse-battery": 514127855860,
    "plc-battery": 159920554084, "pda-pocket-pc-battery": 159760875620,
    "camera-battery": 159760351332, "drones-battery": 394176463092,
    "battery-grip-1": 394177085684, "home-security-camera-battery": 159929040996,
    "thermal-camera-battery": 159924256868, "speaker-battery": 159915769956,
    "gps-navigator-battery": 159759990884, "media-player-battery": 514118910196,
    "game-console-battery": 514127823092, "ebook-ereader-battery": 159917408356,
    "two-way-radio-battery": 159915901028, "cordless-phone-battery": 159760121956,
    "wireless-headset-battery": 159916425316, "hotspot-battery": 159921635428,
    "babyphone-battery": 159925928036, "satellite-phone-battery": 159920652388,
    "power-tools-battery": 159760580708, "equipment-survey-test-battery": 514118877428,
    "barcode-scanner-battery-1": 514118844660, "payment-terminal-battery": 159917932644,
    "microscope-battery": 159955746916, "vacuum-battery": 159916130404,
    "lawn-mowers-battery": 159916261476, "dog-collar-battery": 159915638884,
    "shaver-battery": 159923109988, "toothbrush-battery": 159760089188,
    "electronic-magnifier-battery": 160184500324, "medical-battery": 159760384100,
}


def leaf(title, handle):
    return {"title": title, "type": "COLLECTION",
            "resourceId": f"gid://shopify/Collection/{COLS[handle]}"}


def group(title, children):
    return {"title": title, "type": "HTTP", "url": "#", "items": children}


ITEMS = [
    group("Phones & Tablets", [
        leaf("Phone & Smartphone", "mobile-smartphone-battery"),
        leaf("Tablet", "tablet-battery"),
        leaf("Smartwatch", "smartwatch-battery")]),
    group("Laptops & Computers", [
        leaf("Laptop & Notebook", "notebook-laptop-battery"),
        leaf("UMPC & Netbook", "umpc-netbook-battery"),
        leaf("Keyboard & Mouse", "keyboard-mouse-battery"),
        leaf("PLC", "plc-battery"),
        leaf("PDA & Pocket PC", "pda-pocket-pc-battery")]),
    group("Cameras & Drones", [
        leaf("Camera", "camera-battery"),
        leaf("Drones", "drones-battery"),
        leaf("Battery Grip", "battery-grip-1"),
        leaf("Security Camera", "home-security-camera-battery"),
        leaf("Thermal Camera", "thermal-camera-battery")]),
    group("Electronics", [
        leaf("Speaker", "speaker-battery"),
        leaf("GPS & Navigator", "gps-navigator-battery"),
        leaf("Media Player", "media-player-battery"),
        leaf("Game Console", "game-console-battery"),
        leaf("eBook & Reader", "ebook-ereader-battery")]),
    group("Communication", [
        leaf("Two-Way Radio", "two-way-radio-battery"),
        leaf("Cordless Phone", "cordless-phone-battery"),
        leaf("Wireless Headset", "wireless-headset-battery"),
        leaf("Mobile Hotspot", "hotspot-battery"),
        leaf("Baby Monitor", "babyphone-battery"),
        leaf("Satellite Phone", "satellite-phone-battery")]),
    group("Tools & Industrial", [
        leaf("Power Tools", "power-tools-battery"),
        leaf("Survey & Test", "equipment-survey-test-battery"),
        leaf("Barcode Scanner", "barcode-scanner-battery-1"),
        leaf("Payment Terminal", "payment-terminal-battery"),
        leaf("Microscope", "microscope-battery")]),
    group("Home & Care", [
        leaf("Vacuum Cleaner", "vacuum-battery"),
        leaf("Lawn Mower", "lawn-mowers-battery"),
        leaf("Dog Collar", "dog-collar-battery"),
        leaf("Shaver & Trimmer", "shaver-battery"),
        leaf("Toothbrush", "toothbrush-battery"),
        leaf("Electronic Magnifier", "electronic-magnifier-battery")]),
    leaf("Medical", "medical-battery"),
    {"title": "Shop All", "type": "CATALOG",
     "url": f"{BASE}/collections/all", "items": []},
]

Q_UPD = """mutation MenuUpdate($id: ID!, $title: String!,
                            $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, items: $items) {
    menu { id title items { title url items { title url } } }
    userErrors { field message }
  } }"""
r = hc.post("graphql.json", json={"query": Q_UPD, "variables": {
    "id": MENU_ID, "title": "Main menu", "items": ITEMS}})
out = r.json()
if out.get("errors"):
    print("== errors:", json.dumps(out["errors"])[:500]); sys.exit(1)
mu = out["data"]["menuUpdate"]
print("== userErrors:", mu.get("userErrors"))
for it in mu.get("menu", {}).get("items", []):
    subs = it.get("items", [])
    print(f"   L1 {it['title']:20} 子{len(subs)}"
          + (f" 首: {subs[0]['title']}->{(subs[0].get('url') or '')[:52]}" if subs else ""))
