# -*- coding: utf-8 -*-
"""导航修剪：撤 7 个 0/0 死入口 + Camera/Battery Grip（用户明示不做）。
组名同步改名避免名不副实。空 collection 一并 unpublish。
"""
import json
import sys
import time

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

COLS = {
    "tablet-battery": 159916785764, "smartwatch-battery": 159918588004,
    "keyboard-mouse-battery": 514127855860, "plc-battery": 159920554084,
    "drones-battery": 394176463092, "home-security-camera-battery": 159929040996,
    "thermal-camera-battery": 159924256868, "speaker-battery": 159915769956,
    "media-player-battery": 514118910196, "game-console-battery": 514127823092,
    "two-way-radio-battery": 159915901028, "cordless-phone-battery": 159760121956,
    "wireless-headset-battery": 159916425316, "hotspot-battery": 159921635428,
    "babyphone-battery": 159925928036, "satellite-phone-battery": 159920652388,
    "power-tools-battery": 159760580708, "barcode-scanner-battery-1": 514118844660,
    "payment-terminal-battery": 159917932644, "microscope-battery": 159955746916,
    "vacuum-battery": 159916130404, "lawn-mowers-battery": 159916261476,
    "dog-collar-battery": 159915638884, "shaver-battery": 159923109988,
    "toothbrush-battery": 159760089188,
    "electronic-magnifier-battery": 160184500324, "medical-battery": 159760384100,
}
# 空集合（线上 0/0）与不做项
DEAD_COLLECTIONS = {
    159760023652: "mobile-smartphone-battery",
    159760285796: "notebook-laptop-battery",
    159760810084: "umpc-netbook-battery",
    159760875620: "pda-pocket-pc-battery",
    159759990884: "gps-navigator-battery",
    159917408356: "ebook-ereader-battery",
    514118877428: "equipment-survey-test-battery",
}


def leaf(title, handle):
    return {"title": title, "type": "COLLECTION",
            "resourceId": f"gid://shopify/Collection/{COLS[handle]}"}


def group(title, children):
    return {"title": title, "type": "HTTP", "url": "#", "items": children}


ITEMS = [
    group("Tablets & Smartwatches", [
        leaf("Tablet", "tablet-battery"),
        leaf("Smartwatch", "smartwatch-battery")]),
    group("Computer Accessories", [
        leaf("Keyboard & Mouse", "keyboard-mouse-battery"),
        leaf("PLC", "plc-battery")]),
    group("Drones & Security", [
        leaf("Drones", "drones-battery"),
        leaf("Security Camera", "home-security-camera-battery"),
        leaf("Thermal Camera", "thermal-camera-battery")]),
    group("Electronics", [
        leaf("Speaker", "speaker-battery"),
        leaf("Media Player", "media-player-battery"),
        leaf("Game Console", "game-console-battery")]),
    group("Communication", [
        leaf("Two-Way Radio", "two-way-radio-battery"),
        leaf("Cordless Phone", "cordless-phone-battery"),
        leaf("Wireless Headset", "wireless-headset-battery"),
        leaf("Mobile Hotspot", "hotspot-battery"),
        leaf("Baby Monitor", "babyphone-battery"),
        leaf("Satellite Phone", "satellite-phone-battery")]),
    group("Tools & Industrial", [
        leaf("Power Tools", "power-tools-battery"),
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
    {"title": "Shop All", "type": "CATALOG", "url": f"{BASE}/collections/all",
     "items": []},
]

# ---- 1) 菜单替换 ----
q = """mutation menuUpdate($id: ID!, $title: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, items: $items) {
    menu { id title items { title url items { title url } } }
    userErrors { field message }
  }
}"""
r = hc.post("graphql.json", json={"query": q, "variables": {
    "id": MENU_ID, "title": "Main menu", "items": ITEMS}})
if "data" not in r.json():
    print("原始响应:", r.text[:800])
    raise SystemExit(1)
out = r.json()["data"]["menuUpdate"]
errs = out.get("userErrors") or []
print("菜单更新:", "OK" if not errs else errs)
for it in out["menu"]["items"]:
    kids = ", ".join(k["title"] for k in it.get("items", []))
    print(f"  - {it['title']}" + (f"  [{kids}]" if kids else ""))

# ---- 2) 空 collection unpublish ----
pub = hc.post("graphql.json", json={"query":
    "{ publications(first: 10) { nodes { id name } } }"})
nodes = pub.json()["data"]["publications"]["nodes"]
os_pub = next(n for n in nodes if "online store" in n["name"].lower())
print(f"\n渠道: {os_pub['name']} ({os_pub['id']})")

uq = """mutation collectionUnpublish($input: CollectionUnpublishInput!) {
  collectionUnpublish(input: $input) {
    collection { id handle }
    userErrors { field message }
  }
}"""
for cid, handle in DEAD_COLLECTIONS.items():
    rr = hc.post("graphql.json", json={"query": uq, "variables": {
        "input": {"id": f"gid://shopify/Collection/{cid}",
                  "collectionPublications": [{"publicationId": os_pub["id"]}]}}})
    if "data" not in rr.json():
        print("  原始响应:", rr.text[:300])
        continue
    d = rr.json()["data"]["collectionUnpublish"]
    ue = d.get("userErrors") or []
    print(f"  unpublish {handle}:", "OK" if not ue else ue)
    time.sleep(0.6)
