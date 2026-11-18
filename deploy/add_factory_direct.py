# -*- coding: utf-8 -*-
"""Factory Direct 区块交付（dry-run 默认 / apply 执行）。
apply 流水线:
  1) 备份 main-product.liquid + templates/product.json 到 deploy/backups/
  2) main-product.liquid: schema 注册 factory_direct block 类型 + when 分支渲染
  3) templates/product.json -> templates/product.factory-direct.json（price block 后插入）
  4) 样板产品 4638608261220 赋模板 template_suffix=factory-direct
  5) 全程回读验证
"""
import json
import re
import shutil
import sys
from datetime import datetime

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
PRODUCT_ID = 4638608261220
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"

c = ShopifyRest(StoreService().get_client(1)).client


def get_asset(key):
    try:
        return c.request("GET", f"themes/{TID}/assets.json",
                         params={"asset[key]": key})["asset"].get("value", "") or ""
    except Exception:
        return ""


def put_asset(key, value):
    c.request("PUT", f"themes/{TID}/assets.json", json_body={"asset": {"key": key, "value": value}})


mp = get_asset("sections/main-product.liquid")
tpl = get_asset("templates/product.json")

# ---- 结构侦察（dry-run 与 apply 共用）----
whens = re.findall(r"\{%-?\s*when '([\w-]+)'", mp)
print("when 分支:", whens)

m = re.search(r"\{%\s*schema\s*%\}(.*?)\{%\s*endschema\s*%\}", mp, re.S)
schema_raw = m.group(1) if m else ""
try:
    schema = json.loads(schema_raw)
    print("schema blocks types:", [b.get("type") for b in schema.get("blocks", [])])
except Exception as e:
    raise SystemExit(f"schema 解析失败: {e}")

t = json.loads(tpl)
main_sec = t["order"][0] if t.get("order") else None
blocks = t["sections"][main_sec]["blocks"]
block_order = t["sections"][main_sec]["block_order"]
print("product.json blocks:", [(b, blocks[b]["type"]) for b in block_order])
print("模板已存在 factory_direct?", "factory_direct" in [blocks[b]["type"] for b in block_order])
print("section 已注册?", "factory_direct" in [b.get("type") for b in schema.get("blocks", [])])

if not APPLY:
    print("\n== DRY-RUN（未做任何修改）==")
    sys.exit(0)

# ---- 1) 备份 ----
stamp = datetime.now().strftime("%Y%m%d_%H%M")
for key in ("sections/main-product.liquid", "templates/product.json"):
    name = key.replace("/", "__")
    shutil.copyfile(f"/dev/stdin", f"/tmp/x") if False else None
    with open(f"/home/jason/shopify-admin/deploy/backups/{stamp}__{name}", "w", encoding="utf-8") as f:
        f.write(get_asset(key))
print("已备份 ->", f"deploy/backups/{stamp}__*")

# ---- 2) main-product.liquid 两处插入 ----
FD_LIQUID = """{%- when 'factory_direct' -%}
                  <div class="fd-note" {{ block.shopify_attributes }}>
                    <div class="fd-note__inner">
                      <span class="fd-note__badge">{{ block.settings.heading | escape }}</span>
                      <p class="fd-note__text">{{ block.settings.text | escape }}</p>
                    </div>
                  </div>
                  <style>
                    .fd-note { margin: 0.4rem 0 1.2rem; }
                    .fd-note__inner {
                      display: flex; flex-direction: column; gap: 0.35rem;
                      border: 1px solid rgba(var(--color-foreground), 0.12); border-radius: 8px;
                      padding: 0.85rem 1rem; background: rgba(var(--color-foreground), 0.02);
                    }
                    .fd-note__badge {
                      font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em;
                      text-transform: uppercase; color: rgb(var(--color-foreground));
                    }
                    .fd-note__text { font-size: 0.86rem; line-height: 1.45; margin: 0; opacity: 0.82; }
                    @media screen and (max-width: 749px) { .fd-note__text { font-size: 0.82rem; } }
                  </style>
"""

FD_SCHEMA = {
    "type": "factory_direct",
    "name": "Factory Direct note",
    "settings": [
        {"type": "text", "id": "heading", "label": "Heading", "default": "Factory Direct — Lowest Official Price"},
        {"type": "textarea", "id": "text", "label": "Text",
         "default": "We are the manufacturer. Marketplaces charge ~15% in seller fees — buy factory direct and those savings go to you."},
    ],
}

# 2a) when 分支：插在 when 'price' 分支之后（即下一个 when 之前）；幂等保护
if "fd-note" in mp:
    print("main-product.liquid 已含 fd-note，跳过插入")
    mp2 = mp
else:
    assert whens.count("price") == 1, "when 'price' 不唯一"
    i_when = mp.find("when 'price'")
    i_next = mp.find("{%- when '", i_when + 10)
    assert i_next > 0, "找不到 price 之后的 when 分支"
    mp2 = mp[:i_next] + FD_LIQUID + mp[i_next:]

# 2b) schema blocks：插在第一个 block 类型之前（与 title 同级）；幂等保护
if any(b.get("type") == "factory_direct" for b in schema.get("blocks", [])):
    print("schema 已注册 factory_direct，跳过")
else:
    i_blocks = mp2.find('"blocks":', mp2.find("{% schema %}"))
    i_open = mp2.find("[", i_blocks)
    first_type = mp2.find('{', i_open)
    fd_json = json.dumps(FD_SCHEMA, ensure_ascii=False, indent=6)
    # 缩进对齐（Dawn schema 内一级缩进 6 空格近似；用解析后重排更稳：直接插 JSON 对象 + 逗号
    mp2 = mp2[:first_type] + fd_json + ",\n      " + mp2[first_type:]

if mp2 != mp:
    put_asset("sections/main-product.liquid", mp2)
    import time
    ok = False
    for _ in range(5):
        time.sleep(2)
        if "fd-note" in get_asset("sections/main-product.liquid"):
            ok = True
            break
    print("main-product.liquid 更新:", "OK" if ok else "回读超时（写入请求已受理，稍后核验）")
else:
    print("main-product.liquid 已含 fd-note，无需更新")

# ---- 3) 新模板 product.factory-direct.json ----
if "factory_direct" in (get_asset("templates/product.factory-direct.json") or ""):
    print("模板已存在，跳过创建")
    t2 = json.loads(get_asset("templates/product.factory-direct.json"))
    print("现有 block_order:", t2["sections"][t2["order"][0]]["block_order"])
else:
    new_bid = None
    for bid in ("fd_note", "fd", "factory"):
        if bid not in blocks:
            new_bid = bid
            break
    blocks[new_bid] = {"type": "factory_direct", "settings": {}}
    block_order.insert(block_order.index(
        [b for b in block_order if blocks[b]["type"] == "price"][0]) + 1, new_bid)
    t["sections"][main_sec]["blocks"] = blocks
    t["sections"][main_sec]["block_order"] = block_order
    put_asset("templates/product.factory-direct.json", json.dumps(t, ensure_ascii=False, indent=2))
    print("模板 product.factory-direct.json 创建 OK（block_order:", block_order, "）")

# ---- 4) 产品赋模板 ----
cur = c.request("GET", f"products/{PRODUCT_ID}.json", params={"fields": "template_suffix"})["product"].get("template_suffix")
if cur == "factory-direct":
    print("产品模板已设置，跳过")
else:
    c.request("PUT", f"products/{PRODUCT_ID}.json",
              json_body={"product": {"id": PRODUCT_ID, "template_suffix": "factory-direct"}})
    p = c.request("GET", f"products/{PRODUCT_ID}.json", params={"fields": "handle,template_suffix"})["product"]
    print(f"产品赋模板: template_suffix={p['template_suffix']!r} handle={p['handle'][:50]}")
