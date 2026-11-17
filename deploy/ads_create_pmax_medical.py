# -*- coding: utf-8 -*-
"""创建 PMax「Medical Battery Estry」系列 (拿到 MC 后建好直接 ENABLE)。

顺序: budget -> 图片资产(PIL) -> 文字资产 -> [MC闸] -> campaign ->
      asset_group -> 链接 -> listing_group_filter(custom_label_0=ad-medical) ->
      ENABLE
断点续跑: deploy/pmax_created.json 记录已建资源。
MC 来源: env MERCHANT_CENTER_ID 或 pmax_created.json 的 mc 键。
"""
import base64
import io
import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
DEP = "/home/jason/shopify-admin/deploy"
STATE = f"{DEP}/pmax_created.json"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"
BUDGET_USD = 20.0
NAME = "PMax Medical Estry"
URL = "https://www.estrybattery.com/collections/medical-battery"

state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(
    STATE) else {}
state.setdefault("mc", None)
state.setdefault("budget", None)
state.setdefault("assets", None)
state.setdefault("texts", None)
state.setdefault("campaign", None)
state.setdefault("asset_group", None)
state.setdefault("linked", None)
state.setdefault("filter_root", None)
state.setdefault("enabled", False)


def token():
    return httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30).json()["access_token"]


H = {"Content-Type": "application/json", "developer-token": "unused"}


def mutate(res, operations, op="create", label=""):
    r = httpx.post(f"{API}/{res}:mutate",
                   headers={**H, "Authorization": f"Bearer {token()}"},
                   json={"operations": [{op: o} for o in operations]},
                   timeout=90)
    try:
        out = r.json()
    except Exception:
        raise RuntimeError(f"{label}: HTTP{r.status_code} {r.text[:180]}")
    if r.status_code != 200:
        msg = ""
        try:
            errs = out["error"]["details"][0]["errors"]
            msg = "; ".join(
                f"{e.get('message', '')[:160]}"
                f"@{(e.get('location') or {}).get('fieldPathElements', '')}"
                for e in errs[:5])
        except Exception:
            msg = r.text[:200]
        raise RuntimeError(f"{label}: HTTP{r.status_code} FULL={r.text[:3200]}")
    return [x.get("resourceName", "") for x in out.get("results", [])]


def save():
    json.dump(state, open(STATE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


MC = state["mc"] or os.environ.get("MERCHANT_CENTER_ID")
print("MC =", MC or "(待用户提供)")

# ---------- 1: budget ----------
if not state["budget"]:
    state["budget"] = mutate(
        "campaignBudgets",
        [{"name": f"Budget {NAME}",
          "amountMicros": str(int(BUDGET_USD * 1_000_000)),
          "explicitlyShared": False,
          "deliveryMethod": "STANDARD"}], label="budget")[0]
    save()
print("budget:", state["budget"])

# ---------- 2: 图片资产 (PIL 生成品牌图) ----------
def img_asset(w, h, lines, fg=(0, 166, 81)):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (w, h), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    try:
        f_big = ImageFont.truetype(
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", int(h * 0.16))
        f_sm = ImageFont.truetype(
            "/usr/share/fonts/dejavu/DejaVuSans.ttf", int(h * 0.075))
    except OSError:
        f_big = f_sm = ImageFont.load_default()
    y = int(h * 0.34)
    dr.text((w // 2, y), lines[0], font=f_big, fill=fg, anchor="mm")
    for ln in lines[1:]:
        y += int(h * 0.17)
        dr.text((w // 2, y), ln, font=f_sm, fill=(27, 42, 65), anchor="mm")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return {"imageAsset": {
        "data": base64.b64encode(buf.getvalue()).decode(),
        "fileSize": str(len(buf.getvalue()))}}


if not state["assets"]:
    ops = [
        {"name": "Estry Marketing 1200x628",
         **img_asset(1200, 628, ["Estry", "Medical Device Batteries",
                                 "Exact Fit | US Stock"])},
        {"name": "Estry Square 1200x1200",
         **img_asset(1200, 1200, ["Estry", "Medical Device", "Batteries"])},
        {"name": "Estry Logo 1200x1200",
         **img_asset(1200, 1200, ["Estry"], fg=(0, 166, 81))},
    ]
    names = mutate("assets", ops, label="images")
    state["assets"] = dict(zip(("MK", "SQ", "LG"), names))
    save()
print("image assets:", state["assets"])

# ---------- 3: 文字资产 ----------
HEADLINES = [
    "Medical Device Batteries", "Replacement Batteries in US",
    "OEM-Fit Medical Batteries", "Fast US Shipping, In Stock",
    "Ventilator & ECG Batteries", "Defibrillator Batteries",
    "Patient Monitor Batteries", "1-Year Warranty, Exact Fit",
]
LONG = [
    "Estry Replacement Batteries for Medical Devices - Ventilators, "
    "ECG & Monitors",
    "Exact-Fit Medical Device Batteries, 1-Year Warranty - Ships from "
    "US Stock",
    "Trusted Batteries for Defibrillators, Patient Monitors & Ultrasound",
]
DESCS = [
    "OEM-fit replacement batteries for medical devices. Fast US "
    "shipping & warranty.",
    "Exact fit for your monitor, ventilator or defibrillator. In "
    "stock, ships from US.",
    "High-capacity cells, exact fit. Order your medical battery "
    "today - US stock.",
]
if not state["texts"]:
    ops = [{"textAsset": {"text": t}} for t in HEADLINES]
    ops += [{"textAsset": {"text": t}} for t in LONG]
    ops += [{"textAsset": {"text": t}} for t in DESCS]
    ops += [{"name": "Estry Business Name",
             "textAsset": {"text": "Estry"}}]
    names = mutate("assets", ops, label="texts")
    state["texts"] = {
        "headlines": names[:len(HEADLINES)],
        "long": names[len(HEADLINES):len(HEADLINES) + len(LONG)],
        "descs": names[len(HEADLINES) + len(LONG):-1],
        "biz": names[-1]}
    save()
print("text assets ok")

# ---------- 4: MC 闸 ----------
if not MC:
    print("\n=== 预算+全套素材已建好; campaign 待 MC ID "
          "(MERCHANT_CENTER_ID 环境变量或改 pmax_created.json 的 mc 键后重跑) ===")
    sys.exit(0)

# ---------- 5: campaign (先 PAUSED, 全链建成后 ENABLE) ----------
if not state["campaign"]:
    state["campaign"] = mutate(
        "campaigns",
        [{"name": NAME, "status": "PAUSED",
          "advertisingChannelType": "PERFORMANCE_MAX",
          "campaignBudget": state["budget"],
          "biddingStrategyType": "MAXIMIZE_CONVERSIONS",
          "maximizeConversions": {},
          "containsEuPoliticalAdvertising":
              "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING",
          "shoppingSetting": {"merchantId": str(MC),
                              "feedLabel": "US"}}], label="campaign")[0]
    save()
print("campaign:", state["campaign"])

# ---------- 6: asset_group ----------
if not state["asset_group"]:
    state["asset_group"] = mutate(
        "assetGroups",
        [{"name": "Medical Batteries", "campaign": state["campaign"],
          "finalUrls": [URL], "path1": "medical-battery",
          "path2": "oem-fit"}], label="asset_group")[0]
    save()
print("asset_group:", state["asset_group"])
AG = state["asset_group"]

# ---------- 7: 链接 asset_group_asset ----------
if not state["linked"]:
    # v25 Brand Guidelines 默认启用: business name + logo 必须挂 campaign 级
    mutate("campaignAssets", [
        {"asset": state["texts"]["biz"], "campaign": state["campaign"],
         "fieldType": "BUSINESS_NAME"},
        {"asset": state["assets"]["LG"], "campaign": state["campaign"],
         "fieldType": "LOGO"},
    ], label="link_campaign_brand")
    ops = []
    for a in state["texts"]["headlines"]:
        ops.append({"asset": a, "assetGroup": AG, "fieldType": "HEADLINE"})
    for a in state["texts"]["long"]:
        ops.append({"asset": a, "assetGroup": AG,
                    "fieldType": "LONG_HEADLINE"})
    for a in state["texts"]["descs"]:
        ops.append({"asset": a, "assetGroup": AG,
                    "fieldType": "DESCRIPTION"})
    ops.append({"asset": state["assets"]["MK"], "assetGroup": AG,
                "fieldType": "MARKETING_IMAGE"})
    ops.append({"asset": state["assets"]["SQ"], "assetGroup": AG,
                "fieldType": "SQUARE_MARKETING_IMAGE"})
    mutate("assetGroupAssets", ops, label="link_assets")
    state["linked"] = True
    save()
print("linked assets ok")

# ---------- 8: listing_group_filter 圈品 (custom_label_0=ad-medical) ----------
# 注意: 临时负ID引用只在 googleAds:mutate 聚合端点支持, 专用端点报 BAD_RESOURCE_ID
if not state["filter_root"]:
    tmp = f"customers/{CID}/assetGroupListingGroupFilters/-1"
    body = {"mutateOperations": [
        {"assetGroupListingGroupFilterOperation": {"create": {
            "resourceName": tmp, "assetGroup": AG,
            "type": "SUBDIVISION", "listingSource": "SHOPPING"}}},
        {"assetGroupListingGroupFilterOperation": {"create": {
            "assetGroup": AG, "type": "UNIT_INCLUDED",
            "listingSource": "SHOPPING",
            "caseValue": {"productCustomAttribute": {"value": "ad-medical",
                                                     "index": 0}},
            "parentListingGroupFilter": tmp}}},
        {"assetGroupListingGroupFilterOperation": {"create": {
            "assetGroup": AG, "type": "UNIT_EXCLUDED",
            "listingSource": "SHOPPING",
            "parentListingGroupFilter": tmp}}},
    ]}
    r = httpx.post(f"{API}/googleAds:mutate",
                   headers={**H, "Authorization": f"Bearer {token()}"},
                   json=body, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f"filter_tree: HTTP{r.status_code} FULL={r.text[:3200]}")
    resp = r.json()["mutateOperationResponses"]
    state["filter_root"] = resp[0]["assetGroupListingGroupFilterResult"][
        "resourceName"]
    state["filter_done"] = True
    save()
print("listing filters ok")

# ---------- 9: ENABLE (以量为主, 建好即上线) ----------
if not state["enabled"]:
    r = httpx.post(
        f"{API}/campaigns:mutate",
        headers={**H, "Authorization": f"Bearer {token()}"},
        json={"operations": [{
            "update": {"resourceName": state["campaign"],
                       "status": "ENABLED"},
            "updateMask": "status"}]},
        timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"enable: HTTP{r.status_code} FULL={r.text[:1500]}")
    state["enabled"] = True
    save()

print(f"\n=== 建成并已 ENABLE (预算 ${BUDGET_USD:.0f}/天, "
      "圈品 custom_label_0=ad-medical, 842 个医疗品) ===")
