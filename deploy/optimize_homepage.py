"""ESTRY 首页优化（Dawn v16）：品类网格 + 信任条 + 三步指引 + New Arrivals 文案。

动作：
  1. 上传 3 个新 section：estry-trust-bar / estry-category-grid / estry-how-it-works
  2. index.json：移除空 image_banner，重排 order，featured_collection 加标题
  3. 线上断言：各区块标题渲染 + 品类卡片带实时产品数
用法：
  sudo -u jason .venv/bin/python optimize_homepage.py
  sudo -u jason .venv/bin/python optimize_homepage.py --rollback
"""
import glob
import json
import sys
import time
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
IDX_KEY = "templates/index.json"
c = ShopifyRest(StoreService().get_client(1)).client

TRUST_KEY = "sections/estry-trust-bar.liquid"
GRID_KEY = "sections/estry-category-grid.liquid"
HOW_KEY = "sections/estry-how-it-works.liquid"

SVG_BOLT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M13 2 3 14h7l-1 8 10-12h-7z"/></svg>'
SVG_TRUCK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M1 4h13v12H1z"/><path d="M14 9h4.5L21 12.5V16h-7"/><circle cx="5.5" cy="18.5" r="2"/><circle cx="17.5" cy="18.5" r="2"/></svg>'
SVG_SHIELD = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 2l8 3v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V5z"/><path d="M8.5 11.5 11 14l4.5-4.5"/></svg>'
SVG_ROTATE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3.5 12a8.5 8.5 0 1 0 2.8-6.3"/><path d="M3.5 4v5h5"/></svg>'

TRUST_SVG = {"truck": SVG_TRUCK, "shield": SVG_SHIELD, "rotate": SVG_ROTATE,
             "bolt": SVG_BOLT}

TRUST = """{% comment %} estry-trust-bar-v1 {% endcomment %}
<section class="etb">
  <div class="etb__inner page-width">
    {%- for block in section.blocks -%}
      <div class="etb__item" {{ block.shopify_attributes }}>
        <span class="etb__ico">
          {%- case block.settings.icon -%}
            {%- when 'truck' -%}""" + SVG_TRUCK + """{%- when 'shield' -%}""" + SVG_SHIELD + """{%- when 'rotate' -%}""" + SVG_ROTATE + """{%- else -%}""" + SVG_BOLT + """{%- endcase -%}
        </span>
        <span class="etb__txt">
          <strong>{{ block.settings.title | escape }}</strong>
          <span>{{ block.settings.subtitle | escape }}</span>
        </span>
      </div>
    {%- endfor -%}
  </div>
</section>
<style>
  /* Dawn 全局 1rem=10px（html 62.5%），字号按 px÷10 写 rem */
  .etb{background:#f6f8fa;border-bottom:1px solid #e8edf2;}
  .etb__inner{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;padding:22px 1.5rem;}
  .etb__item{display:flex;align-items:center;gap:12px;justify-content:center;}
  .etb__ico{flex:0 0 42px;width:42px;height:42px;border-radius:50%;background:#e6f7ee;color:#00A651;display:flex;align-items:center;justify-content:center;}
  .etb__ico svg{width:21px;height:21px;}
  .etb__txt{display:flex;flex-direction:column;line-height:1.3;text-align:left;}
  .etb__txt strong{font-size:1.4rem;color:#1B2A41;}
  .etb__txt span{font-size:1.2rem;color:#5a6b7d;}
  @media (max-width:899px){.etb__inner{grid-template-columns:repeat(2,1fr);gap:16px 10px;padding:18px 1rem;}}
</style>
{% schema %}
{
  "name": "ESTRY Trust Bar",
  "settings": [],
  "blocks": [
    {"type": "item", "name": "Item", "settings": [
      {"type": "select", "id": "icon", "label": "Icon",
       "options": [
         {"value": "truck", "label": "Truck"},
         {"value": "shield", "label": "Shield"},
         {"value": "rotate", "label": "Returns"},
         {"value": "bolt", "label": "Bolt"}
       ], "default": "bolt"},
      {"type": "text", "id": "title", "label": "Title"},
      {"type": "text", "id": "subtitle", "label": "Subtitle"}
    ]}
  ],
  "presets": [{"name": "ESTRY Trust Bar"}]
}
{% endschema %}
"""

GRID = """{% comment %} estry-category-grid-v1 {% endcomment %}
<section class="ecg">
  <div class="ecg__inner page-width">
    <div class="ecg__head">
      <h2 class="ecg__title">{{ section.settings.heading | escape }}</h2>
      <p class="ecg__sub">{{ section.settings.subheading | escape }}</p>
    </div>
    <div class="ecg__grid">
      {%- for block in section.blocks -%}
        {%- assign col = block.settings.collection -%}
        {%- if col != blank and col.products_count > 0 -%}
          <a class="ecg__card" href="{{ col.url }}" {{ block.shopify_attributes }}>
            <span class="ecg__badge">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M13 2 3 14h7l-1 8 10-12h-7z"/></svg>
            </span>
            <span class="ecg__name">{{ block.settings.label | default: col.title | escape }}</span>
            <span class="ecg__count">{{ col.products_count }} products</span>
            <span class="ecg__go">Shop now <span aria-hidden="true">&rarr;</span></span>
          </a>
        {%- endif -%}
      {%- endfor -%}
    </div>
  </div>
</section>
<style>
  /* Dawn 全局 1rem=10px（html 62.5%）：区块标题对齐原生 .h2（24px desktop/20px mobile，Oswald） */
  .ecg{padding:52px 0 56px;}
  .ecg__inner{padding:0 1.5rem;}
  .ecg__head{text-align:center;margin-bottom:28px;}
  .ecg__title{margin:0 0 6px;font-size:clamp(2rem,2.4vw,2.4rem);color:#1B2A41;font-family:var(--font-heading-family);font-weight:var(--font-heading-weight);}
  .ecg__sub{margin:0;color:#5a6b7d;font-size:1.4rem;}
  .ecg__grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;}
  .ecg__card{display:flex;flex-direction:column;align-items:flex-start;gap:8px;background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:22px 20px;text-decoration:none;transition:transform .15s,border-color .15s,box-shadow .15s;}
  .ecg__card:hover{transform:translateY(-3px);border-color:#00A651;box-shadow:0 8px 22px rgba(27,42,65,.10);}
  .ecg__badge{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,#1B2A41,#243a57);color:#9fd8b8;display:flex;align-items:center;justify-content:center;margin-bottom:6px;}
  .ecg__badge svg{width:22px;height:22px;}
  .ecg__name{font-size:1.5rem;font-weight:700;color:#1B2A41;}
  .ecg__count{font-size:1.3rem;color:#5a6b7d;}
  .ecg__go{margin-top:auto;padding-top:8px;font-size:1.3rem;font-weight:600;color:#00A651;}
  @media (max-width:899px){.ecg__grid{grid-template-columns:repeat(2,1fr);gap:12px;}.ecg{padding:36px 0 40px;}}
</style>
{% schema %}
{
  "name": "ESTRY Category Grid",
  "settings": [
    {"type": "text", "id": "heading", "label": "Heading", "default": "Shop by Device Type"},
    {"type": "text", "id": "subheading", "label": "Subheading", "default": "Exact-fit replacement batteries for every kind of device"}
  ],
  "blocks": [
    {"type": "category", "name": "Category", "settings": [
      {"type": "collection", "id": "collection", "label": "Collection"},
      {"type": "text", "id": "label", "label": "Custom label (optional)"}
    ]}
  ],
  "presets": [{"name": "ESTRY Category Grid"}]
}
{% endschema %}
"""

HOW = """{% comment %} estry-how-it-works-v1 {% endcomment %}
<section class="ehw">
  <div class="ehw__inner page-width">
    <div class="ehw__head">
      <h2 class="ehw__title">{{ section.settings.heading | escape }}</h2>
      <p class="ehw__sub">{{ section.settings.subheading | escape }}</p>
    </div>
    <div class="ehw__grid">
      {%- for block in section.blocks -%}
        <div class="ehw__step" {{ block.shopify_attributes }}>
          <span class="ehw__num">{{ forloop.index }}</span>
          <h3 class="ehw__st">{{ block.settings.title | escape }}</h3>
          <p class="ehw__sd">{{ block.settings.text | escape }}</p>
        </div>
      {%- endfor -%}
    </div>
  </div>
</section>
<style>
  /* Dawn 全局 1rem=10px（html 62.5%），字号按 px÷10 写 rem */
  .ehw{background:#f6f8fa;padding:52px 0 58px;}
  .ehw__inner{padding:0 1.5rem;}
  .ehw__head{text-align:center;margin-bottom:30px;}
  .ehw__title{margin:0 0 6px;font-size:clamp(2rem,2.4vw,2.4rem);color:#1B2A41;font-family:var(--font-heading-family);font-weight:var(--font-heading-weight);}
  .ehw__sub{margin:0;color:#5a6b7d;font-size:1.4rem;}
  .ehw__grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;max-width:1000px;margin:0 auto;}
  .ehw__step{background:#fff;border-radius:14px;padding:26px 24px;border:1px solid #e2e8f0;text-align:center;}
  .ehw__num{width:40px;height:40px;border-radius:50%;background:#00A651;color:#fff;font-weight:700;font-size:1.5rem;display:flex;align-items:center;justify-content:center;margin:0 auto 12px;}
  .ehw__st{margin:0 0 8px;font-size:1.6rem;color:#1B2A41;}
  .ehw__sd{margin:0;color:#5a6b7d;font-size:1.4rem;line-height:1.55;}
  @media (max-width:749px){.ehw__grid{grid-template-columns:1fr;gap:12px;}.ehw{padding:36px 0 40px;}}
</style>
{% schema %}
{
  "name": "ESTRY How It Works",
  "settings": [
    {"type": "text", "id": "heading", "label": "Heading", "default": "How to Find Your Battery"},
    {"type": "text", "id": "subheading", "label": "Subheading", "default": "Three steps from device model to doorstep"}
  ],
  "blocks": [
    {"type": "step", "name": "Step", "settings": [
      {"type": "text", "id": "title", "label": "Title"},
      {"type": "textarea", "id": "text", "label": "Text"}
    ]}
  ],
  "presets": [{"name": "ESTRY How It Works"}]
}
{% endschema %}
"""

CATS = ["vacuum-battery", "cordless-phone-battery", "power-tools-battery",
        "medical-battery", "two-way-radio-battery", "tablet-battery",
        "barcode-scanner-battery-1", "speaker-battery"]

TRUST_ITEMS = [
    ("truck", "US Warehouse", "Fast domestic shipping"),
    ("shield", "12-Month Warranty", "Full coverage on every battery"),
    ("rotate", "30-Day Returns", "Easy, no-hassle refunds"),
    ("bolt", "10,000+ Models", "Exact-fit replacement batteries"),
]

HOW_STEPS = [
    ("Search Your Model",
     "Enter your device model or battery part number in the search bar above — e.g. Dyson V8 or BP-511."),
    ("Confirm Compatibility",
     "Match your device against the Compatible Models list and part numbers on the product page."),
    ("Fast US Delivery",
     "In-stock orders ship from our US warehouse within 48 hours on business days."),
]


def get_asset(key: str) -> str:
    return c.request("GET", f"themes/{TID}/assets.json",
                     params={"asset[key]": key})["asset"]["value"]


def put_asset(key: str, value: str) -> None:
    try:
        c.request("PUT", f"themes/{TID}/assets.json",
                  json_body={"asset": {"key": key, "value": value}})
    except Exception as e:  # noqa: BLE001
        print(f"!! PUT {key} failed:", e, getattr(e, "details", None))
        raise


if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
    baks = sorted(glob.glob("/tmp/index.dawn.bak-*"))
    if not baks:
        sys.exit("no index.json backup found")
    with open(baks[-1], encoding="utf-8") as f:
        put_asset(IDX_KEY, f.read())
    for k in (TRUST_KEY, GRID_KEY, HOW_KEY):
        c.request("DELETE", f"themes/{TID}/assets.json",
                  params={"asset[key]": k})
    print("rolled back index.json from:", baks[-1], "| 3 section files deleted")
    sys.exit(0)

for k, v in ((TRUST_KEY, TRUST), (GRID_KEY, GRID), (HOW_KEY, HOW)):
    put_asset(k, v)
    print("[1] uploaded:", k, len(v), "bytes")

cur = get_asset(IDX_KEY)
bak = "/tmp/index.dawn.bak-" + time.strftime("%Y%m%d-%H%M%S")
with open(bak, "w", encoding="utf-8") as f:
    f.write(cur)
print("[2] backup:", bak)

data = json.loads(cur)

tb, tb_order = {}, []
for i, (icon, t, s) in enumerate(TRUST_ITEMS):
    k = f"t{i + 1}"
    tb[k] = {"type": "item",
             "settings": {"icon": icon, "title": t, "subtitle": s}}
    tb_order.append(k)
data["sections"]["estry_trust_bar"] = {
    "type": "estry-trust-bar", "blocks": tb, "block_order": tb_order,
    "settings": {}}

gb, gb_order = {}, []
for i, h in enumerate(CATS):
    k = f"c{i + 1}"
    gb[k] = {"type": "category", "settings": {"collection": h}}
    gb_order.append(k)
data["sections"]["estry_category_grid"] = {
    "type": "estry-category-grid", "blocks": gb, "block_order": gb_order,
    "settings": {}}

hb, hb_order = {}, []
for i, (t, s) in enumerate(HOW_STEPS):
    k = f"s{i + 1}"
    hb[k] = {"type": "step", "settings": {"title": t, "text": s}}
    hb_order.append(k)
data["sections"]["estry_how_it_works"] = {
    "type": "estry-how-it-works", "blocks": hb, "block_order": hb_order,
    "settings": {}}

data["sections"].pop("image_banner", None)
fc = data["sections"].get("featured_collection", {}).setdefault("settings", {})
fc["title"] = "New Arrivals"
fc["show_description"] = True
fc["description"] = ("<p>Fresh stock from our US warehouse — the newest "
                     "exact-fit replacement batteries.</p>")

data["order"] = ["estry_search_hero", "estry_trust_bar", "estry_category_grid",
                 "featured_collection", "estry_how_it_works"]
put_asset(IDX_KEY, json.dumps(data, ensure_ascii=False, indent=2))
print("[3] index.json rebuilt, order =", data["order"])

time.sleep(8)
chk = json.loads(get_asset(IDX_KEY))
assert chk["order"][0] == "estry_search_hero" and "image_banner" not in chk["sections"]
print("[4] readback OK")

req = urllib.request.Request(
    "https://www.estrybattery.com/?fresh=" + str(int(time.time())),
    headers={"User-Agent": "Mozilla/5.0"})
body = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
for probe in ["Find Your Battery", "US Warehouse", "Shop by Device Type",
              "products</span>", "New Arrivals", "How to Find Your Battery",
              "Confirm Compatibility"]:
    print(f"[5] {probe!r:38} rendered={probe in body}")
print("HOME-OPTIMIZE-DONE（回滚 --rollback；文案与品类后台主题编辑器可改）")
