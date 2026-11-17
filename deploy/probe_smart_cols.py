# -*- coding: utf-8 -*-
"""smart collections 规则盘点（只读）：78 个现有集合的标题/规则/发布态。"""
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")


def main() -> None:
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)
    cols = []
    since = None
    while True:
        params = {"limit": 250}
        if since:
            params["since_id"] = since
        page = c.request("GET", "smart_collections.json", params=params).get("smart_collections", [])
        if not page:
            break
        cols.extend(page)
        since = page[-1]["id"]
        if len(page) < 250:
            break
    print(f"smart_collections 共 {len(cols)}")
    for s in sorted(cols, key=lambda x: -(x.get("products_count") or 0)):
        r = (s.get("rules") or [{}])[0]
        print(f"  id={s['id']}  published={'Y' if s.get('published_at') else 'N'}  "
              f"n={s.get('products_count') or 0:5}  {s['title'][:40]!r:44}  "
              f"rule: {r.get('column')} {r.get('relation')} {str(r.get('condition'))[:30]!r}")

    custom = c.request("GET", "custom_collections.json", params={"limit": 250}).get("custom_collections", [])
    print(f"\ncustom_collections 共 {len(custom)}")
    for s in custom:
        print(f"  id={s['id']}  published={'Y' if s.get('published_at') else 'N'}  "
              f"n={s.get('products_count')}  {s['title']!r}")

    print("\nSMART-PROBE-OK")


if __name__ == "__main__":
    main()
