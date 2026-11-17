"""写 Dawn 品牌配置（Estry 色板 / Oswald 标题 / 品牌文案），备份原值，复读断言。

色板映射（工业信赖感 + 能量绿点缀）：
  scheme-1 主     白底深蓝按钮（默认页头/主区块）
  scheme-2 次浅灰 F7F9FB 底（卡片/次级区块）
  scheme-3 能量绿 CTA 白底绿钮（强调区块）
  scheme-4 深蓝反白 1B2A41 底（富内容/页脚）
  scheme-5 中蓝横幅 243B53 底琥珀钮（备用强调）
"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
KEY = "config/settings_data.json"
c = ShopifyRest(StoreService().get_client(1)).client


def get_val() -> str:
    return c.request("GET", f"themes/{TID}/assets.json",
                     params={"asset[key]": KEY})["asset"]["value"]


cur_val = get_val()
bak = f"/tmp/settings_data.dawn.bak-{time.strftime('%Y%m%d-%H%M%S')}"
with open(bak, "w", encoding="utf-8") as f:
    f.write(cur_val)
print("backup:", bak)

sd = json.loads(cur_val)
cur = sd["current"]

SCHEMES = {
    "scheme-1": {"background": "#FFFFFF", "background_gradient": "",
                 "text": "#1F2933", "button": "#1B2A41", "button_label": "#FFFFFF",
                 "secondary_button_label": "#243B53", "shadow": "#1B2A41"},
    "scheme-2": {"background": "#F7F9FB", "background_gradient": "",
                 "text": "#52606D", "button": "#243B53", "button_label": "#FFFFFF",
                 "secondary_button_label": "#243B53", "shadow": "#243B53"},
    "scheme-3": {"background": "#FFFFFF", "background_gradient": "",
                 "text": "#1F2933", "button": "#00A651", "button_label": "#FFFFFF",
                 "secondary_button_label": "#00A651", "shadow": "#00A651"},
    "scheme-4": {"background": "#1B2A41", "background_gradient": "",
                 "text": "#FFFFFF", "button": "#00A651", "button_label": "#FFFFFF",
                 "secondary_button_label": "#FFFFFF", "shadow": "#0F1A29"},
    "scheme-5": {"background": "#243B53", "background_gradient": "",
                 "text": "#FFFFFF", "button": "#F5A623", "button_label": "#1B2A41",
                 "secondary_button_label": "#FFFFFF", "shadow": "#10203A"},
}
cur["color_schemes"] = {sid: {"settings": v} for sid, v in SCHEMES.items()}
cur["type_header_font"] = "oswald_n6"          # Oswald SemiBold：工业感标题
cur["brand_headline"] = "Estry. Power You Can Trust."
cur["brand_description"] = ("Premium replacement batteries engineered for safety "
                            "and reliability. Find the exact fit for your device — "
                            "spec-checked, quality-tested, and backed by a 12-month "
                            "warranty.")

c.request("PUT", f"themes/{TID}/assets.json",
          json_body={"asset": {"key": KEY,
                               "value": json.dumps(sd, ensure_ascii=False)}})
time.sleep(6)  # 资产读传播延迟

chk = json.loads(get_val())["current"]
ok_font = chk.get("type_header_font") == "oswald_n6"
ok_scheme = (chk.get("color_schemes", {}).get("scheme-1", {})
             .get("settings", {}).get("button")) == "#1B2A41"
ok_brand = "Estry" in (chk.get("brand_headline") or "")
n_scheme = len(chk.get("color_schemes", {}))
print(f"applied: font={ok_font} scheme1-btn={ok_scheme} brand={ok_brand} "
      f"schemes={n_scheme} | bytes: {len(cur_val)} -> {len(get_val())}")
sys.exit(0 if ok_font and ok_scheme and ok_brand and n_scheme == 5 else 1)
