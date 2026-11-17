# -*- coding: utf-8 -*-
"""Estry B2B 入口注入 (四件套之五).

  A. main-product.liquid: buy_buttons 区块后注入 View Specs / Bulk Quote 双按钮
  B. 首页 estry-search-hero.liquid: 搜索提交跳转 /pages/battery-search + Spec Finder chip
  C. 主导航加 Wholesale 项
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python add_b2b_entry.py --probe   # 仅查看锚点
  sudo -u jason env HOME=/home/jason .venv/bin/python add_b2b_entry.py           # 执行注入
  sudo -u jason env HOME=/home/jason .venv/bin/python add_b2b_entry.py --rollback
"""
import json
import sys
import time
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

TID = 190031036660
MARK = "estry-b2b-v1"
c = ShopifyRest(StoreService().get_client(1)).client


def get_asset(key):
    return c.request("GET", f"themes/{TID}/assets.json",
                     params={"asset[key]": key})["asset"]["value"]


def put_asset(key, value):
    c.request("PUT", f"themes/{TID}/assets.json",
              json_body={"asset": {"key": key, "value": value}})


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (estry-deploy)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""


MP_KEY = "sections/main-product.liquid"
HERO_KEY = "sections/estry-search-hero.liquid"
TIER_MARK = "estry-tier-v1"

# 数量阶梯价格表 (注入在 estry-b2b-cta 双按钮块内, endif 前)
TIER_BLOCK = """                  {%- comment %} estry-tier-v1: volume tier pricing {% endcomment -%}
                  <div class="estry-tier">
                    <div class="etier__t">Volume discounts &mdash; automatic at checkout</div>
                    <table class="etier__tbl">
                      <thead><tr><th>Quantity</th><th>Discount</th><th>Unit price</th></tr></thead>
                      <tbody>
                        <tr><td>10+ pcs</td><td>&minus;5%</td><td class="etier__p">{{ product.selected_or_first_available_variant.price | times: 0.95 | money }}</td></tr>
                        <tr><td>20+ pcs</td><td>&minus;6%</td><td class="etier__p">{{ product.selected_or_first_available_variant.price | times: 0.94 | money }}</td></tr>
                        <tr><td>50+ pcs</td><td>&minus;8%</td><td class="etier__p">{{ product.selected_or_first_available_variant.price | times: 0.92 | money }}</td></tr>
                        <tr><td>100+ pcs</td><td>&minus;10%</td><td class="etier__p">{{ product.selected_or_first_available_variant.price | times: 0.90 | money }}</td></tr>
                      </tbody>
                    </table>
                    <p class="etier__note">Counts your whole cart &mdash; mix &amp; match any models. Applied automatically at checkout.</p>
                  </div>
                  <style>
                    .estry-tier{margin:14px 0 4px;border:1px solid #D9E2EC;border-radius:10px;overflow:hidden;}
                    .etier__t{padding:10px 14px;font-size:1.35rem;font-weight:700;color:#1B2A41;background:#F5F8FB;font-family:var(--font-heading-family);}
                    .etier__tbl{width:100%;border-collapse:collapse;font-size:1.3rem;}
                    .etier__tbl th,.etier__tbl td{padding:8px 14px;text-align:left;border-top:1px solid #EAF0F6;}
                    .etier__tbl thead th{color:#5A6B7F;font-weight:600;font-size:1.2rem;}
                    .etier__tbl td{color:#1B2A41;}
                    .etier__p{color:#008A43;font-weight:700;white-space:nowrap;}
                    .etier__note{margin:0;padding:8px 14px;font-size:1.2rem;color:#5A6B7F;background:#F5F8FB;border-top:1px solid #EAF0F6;}
                    @media (max-width:749px){.etier__tbl th,.etier__tbl td{padding:7px 10px;}}
                  </style>
"""

def get_asset_retry(key, needle, tries=4, wait=5):
    for i in range(tries):
        v = get_asset(key)
        if needle in v:
            return v
        if i < tries - 1:
            time.sleep(wait)
    raise AssertionError(f"{key}: '{needle}' not found after {tries} tries")


if len(sys.argv) > 1 and sys.argv[1] == "--probe":
    mp = get_asset(MP_KEY)
    lines = mp.splitlines()
    for i, ln in enumerate(lines):
        if "when 'buy_buttons'" in ln:
            for j in range(i, min(i + 55, len(lines))):
                print(f"{j+1}: {lines[j][:110]}")
            break
    print("---- hero form ----")
    hero = get_asset(HERO_KEY)
    for i, ln in enumerate(hero.splitlines()):
        if "form" in ln or "hidden" in ln:
            print(f"{i+1}: {ln[:120]}")
    sys.exit(0)

# ---- A. main-product.liquid 注入 (buy_buttons 分支内, buy-buttons snippet 渲染后) ----
INJECT = """
                  {%- comment %} estry-b2b-v1: spec/bulk CTA {% endcomment -%}
                  {%- assign estry_sku = product.selected_or_first_available_variant.sku -%}
                  {%- assign estry_csid = estry_sku | split: '_' | first -%}
                  {%- if estry_csid contains 'CS-' -%}
                  <div class="estry-b2b-cta">
                    <a class="eb2b-btn eb2b-btn--spec" href="/pages/specification?m={{ estry_csid | url_encode }}">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M9 15h6M9 11h2"/></svg>
                      View Full Specs
                    </a>
                    <a class="eb2b-btn eb2b-btn--quote" href="/pages/wholesale?sku={{ estry_sku | url_encode }}">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 3v18h18"/><path d="m7 15 4-6 4 3 5-8"/></svg>
                      Bulk Quote
                    </a>
                  </div>
                  <style>
                    .estry-b2b-cta{display:flex;gap:10px;margin:14px 0 4px;flex-wrap:wrap;}
                    .eb2b-btn{display:inline-flex;align-items:center;gap:7px;padding:10px 16px;border-radius:8px;font-size:1.35rem;font-weight:700;text-decoration:none;transition:all .15s;flex:1;justify-content:center;min-width:150px;}
                    .eb2b-btn svg{width:15px;height:15px;}
                    .eb2b-btn--spec{border:1.5px solid #008A43;color:#008A43;background:#fff;}
                    .eb2b-btn--spec:hover{background:#00A651;border-color:#00A651;color:#fff;}
                    .eb2b-btn--quote{border:1.5px solid #1B2A41;color:#1B2A41;background:#1B2A41;}
                    .eb2b-btn--quote:hover{background:#243a57;border-color:#243a57;color:#fff;}
                  </style>
                  {%- endif -%}
"""

mp = get_asset(MP_KEY).replace("\r\n", "\n")
if MARK in mp:
    print("[A] main-product 已注入, 跳过")
else:
    anchor = "show_pickup_availability: true\n                  -%}\n"
    idx = mp.find(anchor)
    assert idx > 0, "anchor not found"
    bak = "/tmp/main-product.bak-" + time.strftime("%Y%m%d-%H%M%S")
    with open(bak, "w", encoding="utf-8") as f:
        f.write(mp)
    mp2 = mp[:idx + len(anchor)] + INJECT + mp[idx + len(anchor):]
    put_asset(MP_KEY, mp2)
    get_asset_retry(MP_KEY, MARK)
    print(f"[A] main-product 注入 OK (backup {bak})")

# ---- A2. main-product 阶梯价格表升级 (estry-b2b-cta 块内 endif 前插入) ----
mp = get_asset(MP_KEY).replace("\r\n", "\n")
if TIER_MARK in mp:
    print("[A2] 阶梯价格表已注入, 跳过")
else:
    old_tail = "</style>\n                  {%- endif -%}"
    assert mp.count(old_tail) == 1, f"tier anchor count={mp.count(old_tail)} != 1"
    bak = "/tmp/main-product-tier.bak-" + time.strftime("%Y%m%d-%H%M%S")
    with open(bak, "w", encoding="utf-8") as f:
        f.write(mp)
    mp2 = mp.replace(old_tail, "</style>\n" + TIER_BLOCK.rstrip("\n") + "\n                  {%- endif -%}", 1)
    put_asset(MP_KEY, mp2)
    get_asset_retry(MP_KEY, TIER_MARK)
    print(f"[A2] 阶梯价格表注入 OK (backup {bak})")

# ---- B. 首页 hero 搜索跳转新搜索页 ----
hero = get_asset(HERO_KEY).replace("\r\n", "\n")
if "battery-search" in hero:
    print("[B] hero 已改造, 跳过")
else:
    bak2 = "/tmp/hero.bak-" + time.strftime("%Y%m%d-%H%M%S")
    with open(bak2, "w", encoding="utf-8") as f:
        f.write(hero)
    hero2 = hero.replace(
        'action="{{ routes.search_url }}"',
        'action="/pages/battery-search"')
    hero2 = hero2.replace(
        '<input type="hidden" name="options[prefix]" value="last">\n', "")
    hero2 = hero2.replace(
        '<input type="hidden" name="type" value="product">\n', "")
    put_asset(HERO_KEY, hero2)
    get_asset_retry(HERO_KEY, "battery-search")
    print(f"[B] hero 搜索改指 battery-search OK (backup {bak2})")

# ---- C. 导航加 Wholesale (menus API 若无权限则给人工指引) ----
mid = None
try:
    lls = c.request("GET", "menus.json")["menus"]
    main = next((l for l in lls if l["handle"] in ("main-menu", "main_menu")), None)
    if main:
        mid = main["id"]
        items = c.request("GET", f"menus/{mid}/items.json")["items"]
        if any("wholesale" in (i.get("url") or "") for i in items):
            print("[C] 导航已有 Wholesale, 跳过")
        else:
            page_wh = c.request("GET", "pages.json",
                                params={"handle": "wholesale"})["pages"][0]
            c.request("POST", f"menus/{mid}/items.json", json_body={
                "menu_item": {"type": "page", "title": "Wholesale",
                              "object_id": page_wh["id"]}})
            print("[C] 导航加 Wholesale OK")
except Exception as e:  # noqa: BLE001
    print(f"[C] menus API 不可用({e}) -> 请后台手动: Navigation > Main menu > "
          "Add menu item > 页面 'Wholesale'(30秒, 已有不重复)")

# ---- 断言 ----
time.sleep(6)
sample = "https://www.estrybattery.com/products/battery-for-zebra-zr138-zr138cr-p1098850"
st, h = fetch(sample + "?f=" + str(int(time.time())))
ok = st == 200 and "estry-b2b-cta" in h and "Bulk Quote" in h
print(f"[D] 产品页 {st} 双按钮={'estry-b2b-cta' in h} 阶梯表={'estry-tier' in h}")
assert ok, "product page inject not live"
assert "estry-tier" in h, "tier table not live"
st2, h2 = fetch("https://www.estrybattery.com/?f=" + str(int(time.time())))
print(f"[E] 首页 hero 指向 battery-search={'/pages/battery-search' in h2}")
assert "/pages/battery-search" in h2
if mid:
    items2 = c.request("GET", f"menus/{mid}/items.json")["items"]
    print(f"[F] 导航项数={len(items2)} "
          f"Wholesale={any('wholesale' in (i.get('url') or '') for i in items2)}")
else:
    print("[F] 导航核对跳过 (menus API 无权限, 后台手动)")

print("ADD-B2B-ENTRY-DONE")
