# -*- coding: utf-8 -*-
"""抽查：断点文件前 3 个 gid 的线上 status。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")


def main() -> None:
    from shopify_admin.services.stores import StoreService
    with open("/tmp/classify_archive_done.txt") as f:
        gids = [l.strip() for l in f if l.strip()][:3]
    print(f"抽查 {len(gids)} 个: {gids}")
    c = StoreService().get_client(1)
    for gid in gids:
        r = c.graphql("{ n: node(id: \"%s\") { ... on Product { id status title } } }" % gid)
        print("  ", (r or {}).get("n"))


if __name__ == "__main__":
    main()
