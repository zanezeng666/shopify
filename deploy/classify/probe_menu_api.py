# -*- coding: utf-8 -*-
"""探测菜单 API 通道：mutation 字段 + Query 侧 menu 入口。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

Q = """
{
  mut: __schema {
    mutationType { fields { name } }
  }
  qt: __type(name: "Query") {
    fields { name args { name } }
  }
}
"""


def main() -> None:
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)
    r = c.graphql(Q) or {}
    muts = [f["name"] for f in
            (((r.get("mut") or {}).get("mutationType") or {}).get("fields")) or []]
    menu_muts = [m for m in muts if "menu" in m.lower() or "link" in m.lower()]
    print("menu/link mutations:", menu_muts)
    qf = [f["name"] for f in (r.get("qt") or {}).get("fields") or []]
    print("Query 含 menu/nav:", [f for f in qf if "menu" in f or "nav" in f.lower()])

    # REST 写通道探测：GET linklists 404 已知；试 HEAD/GET linklists/count.json
    try:
        rr = c.request("GET", "linklists/count.json")
        print("REST linklists/count:", rr)
    except Exception as e:  # noqa: BLE001
        print("REST linklists/count ERR:", str(e)[:120])


if __name__ == "__main__":
    main()
