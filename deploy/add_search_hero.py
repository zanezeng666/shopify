"""ESTRY 首页大搜索框 Hero（Dawn v16）。

电池替换站核心动线 = 型号搜索，Dawn 默认首页无搜索框（header 只有小图标）。
本脚本：
  1. 上传 sections/estry-search-hero.liquid（大号搜索框 + 热门类目 chips）
  2. templates/index.json 顶部注入该 section（备份可回滚）
  3. 线上断言：首页渲染出搜索表单 + /search 通路 200
用法：
  sudo -u jason .venv/bin/python add_search_hero.py
  sudo -u jason .venv/bin/python add_search_hero.py --rollback
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
SEC_KEY = "sections/estry-search-hero.liquid"
IDX_KEY = "templates/index.json"
MARK = "estry-search-hero-v1"
HOME = "https://www.estrybattery.com/"
c = ShopifyRest(StoreService().get_client(1)).client

CHIPS = [
    ("Vacuum", "/collections/vacuum-battery"),
    ("Cordless Phone", "/collections/cordless-phone-battery"),
    ("Power Tools", "/collections/power-tools-battery"),
    ("Medical", "/collections/medical-battery"),
    ("Two-Way Radio", "/collections/two-way-radio-battery"),
    ("Barcode Scanner", "/collections/barcode-scanner-battery-1"),
]

SECTION = """{% comment %} estry-search-hero-v1: homepage big search {% endcomment %}
<section class="esh" role="region" aria-label="Battery search">
  <div class="esh__inner page-width">
    <p class="esh__kicker">{{ section.settings.kicker | escape }}</p>
    <h2 class="esh__title">{{ section.settings.heading | escape }}</h2>
    <form action="{{ routes.search_url }}" method="get" role="search" class="esh__form">
      <input type="hidden" name="options[prefix]" value="last">
      <input type="hidden" name="type" value="product">
      <input class="esh__input" type="search" name="q" value="{{ search.terms | escape }}"
             placeholder="{{ section.settings.placeholder | escape }}"
             aria-label="Search batteries" autocomplete="off">
      <button type="submit" class="esh__btn">
        <svg class="esh__ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true" focusable="false"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21"/></svg>
        <span>{{ section.settings.button_label | escape }}</span>
      </button>
    </form>
    <div class="esh__chips">
      {%- for block in section.blocks -%}
        {%- if block.settings.label != blank -%}
          <a class="esh__chip" href="{{ block.settings.link }}" {{ block.shopify_attributes }}>{{ block.settings.label | escape }}</a>
        {%- endif -%}
      {%- endfor -%}
    </div>
  </div>
</section>

<style>
  /* 字号说明：Dawn 全局 html{font-size:62.5%}，1rem=10px——按 px÷10 写 rem */
  .esh{background:linear-gradient(135deg,#1B2A41 0%,#243a57 55%,#16233a 100%);}
  .esh__inner{padding:56px 1.5rem 48px;text-align:center;color:#fff;}
  .esh__kicker{margin:0 0 8px;font-size:1.2rem;letter-spacing:.12em;text-transform:uppercase;color:#9fd8b8;font-family:var(--font-heading-family);font-weight:var(--font-heading-weight);}
  .esh__title{margin:0 0 24px;font-size:clamp(2.6rem,4vw,3.6rem);line-height:1.15;color:#fff;font-family:var(--font-heading-family);font-weight:var(--font-heading-weight);}
  .esh__form{display:flex;gap:10px;max-width:760px;margin:0 auto;}
  .esh__input{flex:1 1 auto;height:58px;border:none;border-radius:10px;padding:0 18px;font-size:1.6rem;color:#1B2A41;background:#fff;outline:none;min-width:0;}
  .esh__input:focus{box-shadow:0 0 0 3px rgba(0,166,81,.4);}
  .esh__btn{flex:0 0 auto;height:58px;padding:0 26px;border:none;border-radius:10px;background:#00A651;color:#fff;font-size:1.6rem;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:8px;transition:background .15s;}
  .esh__btn:hover{background:#008a43;}
  .esh__ico{width:20px;height:20px;}
  .esh__chips{margin-top:20px;display:flex;flex-wrap:wrap;gap:10px;justify-content:center;}
  .esh__chip{padding:7px 16px;border-radius:999px;background:rgba(255,255,255,.10);color:#e8eef5;font-size:1.3rem;text-decoration:none;border:1px solid rgba(255,255,255,.16);transition:background .15s,border-color .15s;}
  .esh__chip:hover{background:#00A651;border-color:#00A651;color:#fff;}
  @media (max-width:749px){
    .esh__inner{padding:40px 1rem 36px;}
    .esh__form{flex-direction:column;}
    .esh__btn{justify-content:center;}
  }
</style>

{% schema %}
{
  "name": "ESTRY Search Hero",
  "settings": [
    {"type": "text", "id": "kicker", "label": "Kicker", "default": "OEM & replacement batteries for 10,000+ device models"},
    {"type": "text", "id": "heading", "label": "Heading", "default": "Find Your Battery in Seconds"},
    {"type": "text", "id": "placeholder", "label": "Search placeholder", "default": "Enter device model, part number or brand (e.g. Dyson V8)"},
    {"type": "text", "id": "button_label", "label": "Button label", "default": "Search"}
  ],
  "blocks": [
    {"type": "chip", "name": "Popular link", "settings": [
      {"type": "text", "id": "label", "label": "Label"},
      {"type": "url", "id": "link", "label": "Link"}
    ]}
  ],
  "presets": [{"name": "ESTRY Search Hero"}]
}
{% endschema %}
"""


def get_asset(key: str) -> str:
    return c.request("GET", f"themes/{TID}/assets.json",
                     params={"asset[key]": key})["asset"]["value"]


def put_asset(key: str, value: str) -> None:
    c.request("PUT", f"themes/{TID}/assets.json",
              json_body={"asset": {"key": key, "value": value}})


def fetch(url: str):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (estry-deploy)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001
        return -1, ""


# ---- rollback ----
if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
    baks = sorted(glob.glob("/tmp/index.dawn.bak-*"))
    if not baks:
        sys.exit("no index.json backup found")
    with open(baks[-1], encoding="utf-8") as f:
        old = f.read()
    put_asset(IDX_KEY, old)
    c.request("DELETE", f"themes/{TID}/assets.json",
              params={"asset[key]": SEC_KEY})
    print("rolled back index.json from:", baks[-1],
          "| section file deleted")

# ---- inject ----
put_asset(SEC_KEY, SECTION)
print("[1] section uploaded:", SEC_KEY, len(SECTION), "bytes")

cur = get_asset(IDX_KEY)
bak = "/tmp/index.dawn.bak-" + time.strftime("%Y%m%d-%H%M%S")
with open(bak, "w", encoding="utf-8") as f:
    f.write(cur)
print("[2] backup:", bak)

data = json.loads(cur)
blocks: dict = {}
order: list[str] = []
for i, (label, link) in enumerate(CHIPS):
    k = f"chip{i + 1}"
    blocks[k] = {"type": "chip",
                 "settings": {"label": label, "link": link}}
    order.append(k)
data["sections"]["estry_search_hero"] = {
    "type": "estry-search-hero",
    "blocks": blocks,
    "block_order": order,
    "settings": {},
}
if "estry_search_hero" not in data["order"]:
    data["order"].insert(0, "estry_search_hero")
put_asset(IDX_KEY, json.dumps(data, ensure_ascii=False, indent=2))
print("[3] index.json injected, order[:3] =", data["order"][:3])

time.sleep(8)
chk = json.loads(get_asset(IDX_KEY))
assert "estry_search_hero" in chk["sections"], "index readback failed"
assert chk["order"][0] == "estry_search_hero", "order readback failed"
print("[4] readback OK")

st, body = fetch(HOME + "?fresh=" + str(int(time.time())))
ok_home = st == 200 and "esh__form" in body and "Find Your Battery" in body
print(f"[5] homepage {st} hero-render={ok_home}")

st2, _ = fetch(HOME + "search?q=dyson&type=product")
print(f"[6] search通路 {st2}")

print("SEARCH-HERO-DONE（回滚 --rollback；文案后台主题编辑器可改）")
