"""UI 修复：① Bulk Quote 按钮默认态白字（原黑底黑字笔误）② Factory Direct 区块字号/风格对齐主题。幂等。"""
import re
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
c = ShopifyRest(StoreService().get_client(1)).client
KEY = "sections/main-product.liquid"

v = c.request("GET", f"themes/{TID}/assets.json", params={"asset[key]": KEY})["asset"]["value"]
print("bytes:", len(v))

# 备份
stamp = time.strftime("%Y%m%d_%H%M")
with open(f"/home/jason/shopify-admin/deploy/backups/{stamp}__sections__main-product.liquid", "w") as f:
    f.write(v)

# ---- ① Bulk Quote 按钮默认态白字 ----
OLD_QUOTE = "color:#1B2A41;background:#1B2A41;"
NEW_QUOTE = "color:#fff;background:#1B2A41;"
if OLD_QUOTE in v:
    v = v.replace(OLD_QUOTE, NEW_QUOTE, 1)
    print("① quote 按钮默认白字: 已修复")
elif NEW_QUOTE in v:
    print("① quote 按钮默认白字: 已是目标值，跳过")
else:
    raise SystemExit("① 未找到 quote 按钮样式串，中止")

# ---- ② Factory Direct 区块排版 ----
NEW_STYLE = """<style>
                    .fd-note { margin: 0.4rem 0 1.2rem; }
                    .fd-note__inner {
                      display: flex; flex-direction: column; gap: 0.4rem;
                      border: 1px solid rgba(var(--color-foreground), 0.12); border-radius: 8px;
                      padding: 1rem 1.1rem; background: rgba(var(--color-foreground), 0.02);
                    }
                    .fd-note__badge {
                      font-size: 0.95rem; font-weight: 700; letter-spacing: 0.01em;
                      color: rgb(var(--color-foreground));
                    }
                    .fd-note__text { font-size: 0.95rem; line-height: 1.5; margin: 0; opacity: 0.9; }
                    @media screen and (max-width: 749px) { .fd-note__text { font-size: 0.92rem; } }
                  </style>"""

pat = re.compile(r"<style>\s*\n\s*\.fd-note \{.*?</style>", re.S)
if "font-size: 0.95rem; font-weight: 700" in v and "fd-note" in v and ".fd-note__badge {\n                      font-size: 0.95rem" in v:
    print("② fd-note 样式: 已是目标值，跳过")
elif pat.search(v):
    v = pat.sub(lambda _: NEW_STYLE, v, count=1)
    print("② fd-note 样式: 已更新（0.95rem / 去大写 / 去宽字距）")
else:
    raise SystemExit("② 未找到 fd-note style 块，中止")

c.request("PUT", f"themes/{TID}/assets.json", json_body={"asset": {"key": KEY, "value": v}})
ok = False
for _ in range(5):
    time.sleep(2)
    chk = c.request("GET", f"themes/{TID}/assets.json", params={"asset[key]": KEY})["asset"]["value"]
    if NEW_QUOTE in chk and "font-size: 0.95rem; font-weight: 700" in chk:
        ok = True
        break
print("回读验证:", "OK" if ok else "超时（写入已受理，稍后复核）")
