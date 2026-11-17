# -*- coding: utf-8 -*-
"""BWT 修复①：给超长标题的 active 产品写 SEO title（metafields_global_title_tag）。
只影响 <title> 标签；页面 h1/正文不变。用法：python bwt_title_fix.py [N]  # N=本次处理上限"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

cl = ShopifyRest(StoreService().get_client(1)).client
LIMIT = 65          # SEO title 目标长度上限
DONE = "/home/jason/shopify-admin/deploy/bwt_title_fix_done.json"

try:
    done = set(json.load(open(DONE)))
except Exception:
    done = set()

allp = json.load(open("/home/jason/shopify-admin/deploy/bwt_audit_result.json"))
todo = [p for p in allp
        if p["status"] == "active" and len(p["title"]) > LIMIT
        and p["id"] not in done]
print(f"待处理 {len(todo)}（已完成 {len(done)}）")

n = int(sys.argv[1]) if len(sys.argv) > 1 else len(todo)


def seo_title(t: str) -> str:
    head = t[:LIMIT - 11]
    head = head.rsplit(" ", 1)[0] if " " in head else head
    rest_tokens = len(t[len(head):].split())
    if rest_tokens <= 1:
        return head
    return f"{head} +{rest_tokens} more"


ok = fail = 0
for p in todo[:n]:
    st = seo_title(p["title"])
    try:
        cl.request("PUT", f"products/{p['id']}.json", json_body={
            "product": {"id": p["id"],
                        "metafields_global_title_tag": st}})
        done.add(p["id"])
        ok += 1
        if ok <= 3 or ok % 100 == 0:
            print(f"  [{len(st)}] {st}")
    except Exception as e:
        fail += 1
        print(f"  FAIL {p['id']}: {str(e)[:120]}")
    with open(DONE, "w") as f:
        json.dump(sorted(done), f)
    time.sleep(0.55)

print(f"\n完成 {ok} 失败 {fail}，累计 {len(done)}")
