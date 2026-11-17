# -*- coding: utf-8 -*-
"""查当前 app token 的 access scopes。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

Q = """
{ currentAppInstallation { accessScopes { handle } } }
"""


def main() -> None:
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)
    r = c.graphql(Q, {}) or {}
    scopes = sorted(s["handle"] for s in
                    ((r.get("currentAppInstallation") or {}).get("accessScopes") or []))
    print(f"scopes ({len(scopes)}):")
    for s in scopes:
        print(f"  {s}")
    need = "write_online_store_navigation"
    print(f"\n{need}: {'YES' if need in scopes else 'MISSING'}")


if __name__ == "__main__":
    main()
