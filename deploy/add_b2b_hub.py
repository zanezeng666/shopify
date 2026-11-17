# -*- coding: utf-8 -*-
"""Estry B2B 入口补强: 首页服务枢纽 + footer 快捷链接.

  1. 上传 sections/estry-b2b-hub.liquid (四卡: 搜索/规格书/询盘/证书)
  2. 注入 templates/index.json (hero 之后)
  3. footer.liquid 注入 B2B 快捷链接行 (锚点 footer__content-bottom-wrapper)
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python add_b2b_hub.py
"""
import json
import sys
import time
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

TID = 190031036660
HUB_KEY = "sections/estry-b2b-hub.liquid"
FOOTER_KEY = "sections/footer.liquid"
c = ShopifyRest(StoreService().get_client(1)).client

HUB = r"""{% comment %} estry-b2b-hub-v1: B2B services hub {% endcomment %}
<section class="ebh" id="ebh-root">
  <div class="page-width">
    <p class="ebh__kicker">B2B &amp; Wholesale Services</p>
    <h2 class="ebh__title">Everything procurement teams need, in one place</h2>
    <div class="ebh__grid">
      <a class="ebh__card" href="/pages/battery-search">
        <span class="ebh__ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21"/></svg></span>
        <span class="ebh__t">Battery Finder</span>
        <span class="ebh__d">Search 8,700+ models by device, brand or OEM part number.</span>
        <span class="ebh__go">Find a battery &rarr;</span>
      </a>
      <a class="ebh__card" href="/pages/specification">
        <span class="ebh__ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2.5h9l4.5 4.5v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-18a1 1 0 0 1 1-1z"/><path d="M14.5 2.5V7h5"/><path d="M8.5 12h7M8.5 15.5h7M8.5 19h4"/></svg></span>
        <span class="ebh__t">Spec Sheets</span>
        <span class="ebh__d">Full electrical &amp; mechanical datasheets for every model &mdash; printable / PDF.</span>
        <span class="ebh__go">View datasheets &rarr;</span>
      </a>
      <a class="ebh__card" href="/pages/wholesale">
        <span class="ebh__ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 8.5 12 3l8.5 5.5v11a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1v-11z"/><path d="M9 12.5h6v6H9z"/><path d="M12 9.5v3M10.5 9.5h3"/></svg></span>
        <span class="ebh__t">Wholesale Quotes</span>
        <span class="ebh__d">Bulk pricing, MOQ-friendly. Send your part list &mdash; quote within 24h.</span>
        <span class="ebh__go">Request a quote &rarr;</span>
      </a>
      <a class="ebh__card" href="/pages/certificates">
        <span class="ebh__ico" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="9" r="5.5"/><path d="m8.8 13.5-1.6 7 4.8-2.6 4.8 2.6-1.6-7"/><path d="m10.2 8.7 1.3 1.4 2.4-2.6"/></svg></span>
        <span class="ebh__t">Certificates</span>
        <span class="ebh__d">UN 38.3 test summaries &amp; MSDS &mdash; free with every wholesale order.</span>
        <span class="ebh__go">Request docs &rarr;</span>
      </a>
    </div>
  </div>
</section>
<style>
  .ebh{--navy:#1B2A41;--green:#00A651;--green-d:#008A43;--line:#D9E2EC;background:#fff;padding:46px 0 34px;}
  .ebh__kicker{margin:0 0 6px;font-size:1.2rem;letter-spacing:.14em;text-transform:uppercase;color:var(--green-d);font-family:var(--font-heading-family);font-weight:var(--font-heading-weight);text-align:center;}
  .ebh__title{margin:0 0 26px;font-size:clamp(2rem,3.4vw,2.9rem);line-height:1.15;color:var(--navy);font-family:var(--font-heading-family);font-weight:var(--font-heading-weight);text-align:center;}
  .ebh__grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;}
  .ebh__card{display:flex;flex-direction:column;gap:8px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:22px 18px 18px;text-decoration:none;transition:all .18s;position:relative;overflow:hidden;}
  .ebh__card::after{content:"";position:absolute;left:0;top:0;width:100%;height:3px;background:linear-gradient(90deg,var(--green),#4cc47f);opacity:0;transition:opacity .18s;}
  .ebh__card:hover{border-color:#bfe5cf;box-shadow:0 6px 22px rgba(27,42,65,.09);transform:translateY(-2px);}
  .ebh__card:hover::after{opacity:1;}
  .ebh__ico{width:42px;height:42px;border-radius:10px;background:#e7f5ed;color:var(--green-d);display:flex;align-items:center;justify-content:center;margin-bottom:4px;}
  .ebh__ico svg{width:22px;height:22px;}
  .ebh__t{font-size:1.65rem;font-weight:700;color:var(--navy);font-family:var(--font-heading-family);}
  .ebh__d{font-size:1.32rem;line-height:1.5;color:#5A6B7F;}
  .ebh__go{margin-top:auto;padding-top:8px;font-size:1.3rem;font-weight:700;color:var(--green-d);}
  .ebh__card:hover .ebh__go{text-decoration:underline;}
  @media (max-width:989px){.ebh__grid{grid-template-columns:repeat(2,1fr);}}
  @media (max-width:570px){.ebh__grid{grid-template-columns:1fr;}}
</style>
{% schema %}
{
  "name": "Estry B2B Hub",
  "settings": [],
  "presets": [{"name": "Estry B2B Hub"}]
}
{% endschema %}
"""

FOOTER_INJECT = """{%- comment %} estry-b2b-links-v1 {% endcomment -%}
        <div class="footer__b2b" style="display:flex;flex-wrap:wrap;gap:6px 20px;justify-content:center;align-items:center;padding:2px 0 12px;font-size:1.3rem;">
          <span style="font-weight:700;color:rgba(18,18,18,.75);">B2B &amp; Wholesale:</span>
          <a href="/pages/battery-search" style="color:rgba(18,18,18,.6);text-decoration:none;">Battery Finder</a>
          <a href="/pages/specification" style="color:rgba(18,18,18,.6);text-decoration:none;">Spec Sheets</a>
          <a href="/pages/wholesale" style="color:rgba(18,18,18,.6);text-decoration:none;">Wholesale Quotes</a>
          <a href="/pages/certificates" style="color:rgba(18,18,18,.6);text-decoration:none;">Certificates</a>
        </div>
"""


def get_asset(key):
    return c.request("GET", f"themes/{TID}/assets.json",
                     params={"asset[key]": key})["asset"]["value"]


def put_asset(key, value):
    c.request("PUT", f"themes/{TID}/assets.json",
              json_body={"asset": {"key": key, "value": value}})


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (estry-deploy)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "ignore")


# ① hub section
put_asset(HUB_KEY, HUB)
time.sleep(1)
assert "estry-b2b-hub-v1" in get_asset(HUB_KEY), "hub readback failed"
print("[1] hub section uploaded:", HUB_KEY)

# ② index.json 注入 (hero 之后)
tpl = json.loads(get_asset("templates/index.json"))
types = [s.get("type", "") for s in tpl.get("sections", {}).values()]
if "estry-b2b-hub" in types:
    print("[2] index.json already has hub, skip")
else:
    key = "b2b-hub"
    while key in tpl.get("sections", {}):
        key += "x"
    tpl.setdefault("sections", {})[key] = {"type": "estry-b2b-hub"}
    order = list(tpl.get("order", list(tpl["sections"].keys())))
    pos = 0
    for i, k in enumerate(order):
        if "hero" in tpl["sections"].get(k, {}).get("type", ""):
            pos = i + 1
    order.insert(pos, key)
    tpl["order"] = order
    put_asset("templates/index.json", json.dumps(tpl, ensure_ascii=False, indent=2))
    time.sleep(1)
    chk = json.loads(get_asset("templates/index.json"))
    assert "estry-b2b-hub" in [s.get("type") for s in chk["sections"].values()], "index readback failed"
    print(f"[2] index.json injected at position {pos}")

# ③ footer 链接行
f = get_asset(FOOTER_KEY).replace("\r\n", "\n")
if "estry-b2b-links-v1" in f:
    print("[3] footer already injected, skip")
else:
    anchors = ['<div class="footer__content-bottom-wrapper', "<footer", "{%- comment -%} footer"]
    hit = next((a for a in anchors if a in f), None)
    assert hit, "footer anchor not found"
    if hit == anchors[0]:
        # 内容底栏 wrapper 开标签结束后、copyright 列之前插入
        idx = f.index(hit)
        end = f.index(">", idx) + 1
        f2 = f[:end] + "\n      " + FOOTER_INJECT.strip() + "\n    " + f[end:]
    else:
        idx = f.index(hit)
        f2 = f[:idx] + FOOTER_INJECT + f[idx:]
    put_asset(FOOTER_KEY, f2)
    time.sleep(1)
    assert "estry-b2b-links-v1" in get_asset(FOOTER_KEY), "footer readback failed"
    print("[3] footer b2b links injected, anchor:", hit.strip())

# ④ 线上断言
time.sleep(3)
for handle, mark in [("battery-search", "ebs-table"), ("", "estry-b2b-hub")]:
    st, h = fetch(f"https://www.estrybattery.com/{'pages/' + handle if handle else ''}?_v={int(time.time())}")
    ok = st == 200 and mark in h
    print(f"[4] /{'pages/' + handle if handle else '(home)'} {st} mark={'OK' if ok else 'MISS'}")
    assert ok, f"live check failed: {handle or 'home'}"

print("DONE")
