# -*- coding: utf-8 -*-
"""Estry 型号库 SEO 页全量批跑（v2 全类目版）.

与 add_model_pages.py 的区别:
  1. 类目=全部可售（排除三类 DRAFT 黑名单，与 sync_shopify 口径一致）
  2. 免每页 GET 查重（done 文件+handle 唯一性兜底，POST 422 再回查）→ 请求减半
  3. 间隔 1.1s + 429 指数退避，全程 ~60 分钟
  4. related 内链=同类目优先
断点: /tmp/model_pages_done.txt（与试点共享）。日志: deploy/model_pages_all.log
用法:
  nohup sudo -u jason env HOME=/home/jason .venv/bin/python deploy/add_model_pages_all.py > deploy/model_pages_all.log 2>&1 &
"""
import json
import sys
import time
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

sys.path.insert(0, "/home/jason/shopify-admin/deploy")
from add_model_pages import DONE, render, slug  # noqa: E402

TID = 190031036660
DRAFT_CATS = {"Mobile, SmartPhone", "Notebook, Laptop", "Camera"}
rest = ShopifyRest(StoreService().get_client(1)).client


def main():
    items = []
    for i in range(3):
        a = rest.request("GET", f"themes/{TID}/assets.json",
                         params={"asset[key]": f"assets/spec-idx-{i}.json"})["asset"]
        items.extend(json.loads(a.get("value") or "[]"))
    sell = [it for it in items if it.get("c") not in DRAFT_CATS]
    sell.sort(key=lambda it: -(len(it.get("fm") or []) + len(it.get("pn") or [])))
    print(f"total={len(items)} sellable={len(sell)}", flush=True)

    by_cat = {}
    for it in sell:
        by_cat.setdefault(it["c"], []).append(it)

    done = set()
    try:
        done = {l.strip() for l in open(DONE) if l.strip()}
    except FileNotFoundError:
        pass

    created = skipped = failed = 0
    for idx, it in enumerate(sell):
        h = slug(it["m"])
        if h in done:
            skipped += 1
            continue
        cat = it["c"]
        pool = by_cat[cat]
        related = [r for r in pool if r["m"] != it["m"]][:4]
        if len(related) < 2:  # 小类目跨类目补足
            for r in sell:
                if r["m"] != it["m"] and r not in related:
                    related.append(r)
                if len(related) >= 4:
                    break
        title, body = render(it, related)
        for attempt in range(4):
            try:
                rest.request("POST", "pages.json", json_body={
                    "page": {"title": title, "handle": h, "body_html": body,
                             "published": True}})
                created += 1
                if created % 100 == 0:
                    print(f"[{idx+1}/{len(sell)}] created={created} skipped={skipped} failed={failed}", flush=True)
                break
            except Exception as e:
                msg = str(getattr(e, "details", "") or e)
                if "429" in str(e)[:120] or "Too Many Attempts" in str(e)[:200]:
                    time.sleep(3 * (attempt + 1))
                    continue
                # handle 已被占（试点曾建过）→ 查到更新
                if "taken" in msg or "already" in msg:
                    try:
                        ex = rest.request("GET", "pages.json",
                                          params={"handle": h, "limit": 1}).get("pages", [])
                        if ex:
                            rest.request("PUT", f"pages/{ex[0]['id']}.json", json_body={
                                "page": {"id": ex[0]["id"], "title": title,
                                         "body_html": body, "published": True}})
                            created += 1
                            print("updated-existing", h, flush=True)
                            break
                    except Exception as e2:
                        print("FAIL-update", h, str(getattr(e2, "details", e2))[:160], flush=True)
                print("FAIL", h, msg[:160], flush=True)
                failed += 1
                break
        with open(DONE, "a") as f:
            f.write(h + "\n")
        time.sleep(1.1)
    print(f"FINISHED created/updated={created} skipped={skipped} failed={failed}", flush=True)

    # 末页线上断言
    if sell:
        h = slug(sell[-1]["m"])
        for _ in range(6):
            try:
                txt = urllib.request.urlopen(
                    f"https://www.estrybattery.com/pages/{h}", timeout=15).read().decode()
                print("live check", h, "PASS" if sell[-1]["m"] in txt else "MISSING", flush=True)
                break
            except Exception:
                time.sleep(15)


if __name__ == "__main__":
    main()
