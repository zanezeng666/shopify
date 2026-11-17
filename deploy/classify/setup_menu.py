# -*- coding: utf-8 -*-
"""二级导航配置：menuCreate 建 'estry-main-menu'（一级分组+二级类目下拉），
Dawn header 绑定切到新菜单。用户要求：分类过多必须二级收纳。

顶级 8 项：Home & Garden / Communication / Power Tools & Equipment / Medical /
Computers & Tablets / Electronics / Business & Industrial / Shop All
用法：python setup_menu.py [--dry]（dry 只打印结构不动 API）
"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

MENU_HANDLE = "estry-main-menu"
THEME_ID = 190031036660  # ESTRY Dawn v16.0.0 (main)

# (顶级显示名, 顶级集合 title 或 SHOP_ALL, [(二级显示名, 集合 title), ...])
GROUPS = [
    ("Home & Garden", "Vacuum Battery", [
        ("Vacuum Cleaner", "Vacuum Battery"),
        ("Lawn Mowers", "Lawn Mowers Battery"),
        ("Dog Collar", "Dog Collar Battery"),
    ]),
    ("Communication", "Two-Way Radio Battery", [
        ("Two-Way Radio", "Two-Way Radio Battery"),
        ("Cordless Phone", "Cordless Phone Battery"),
        ("Wireless Headset", "Wireless Headset Battery"),
        ("Mobile Hotspot", "Hotspot Battery"),
    ]),
    ("Power Tools & Equipment", "Power Tools Battery", [
        ("Power Tools", "Power Tools Battery"),
        ("Survey & Test Equipment", "Equipment, Survey, Test Battery"),
        ("Portable Printer", "Portable Printer Battery"),
    ]),
    ("Medical", "Medical Battery", []),
    ("Computers & Tablets", "Tablet Battery", [
        ("Tablet", "Tablet Battery"),
        ("Keyboard & Mouse", "Keyboard,Mouse Battery"),
        ("PLC", "PLC Battery"),
    ]),
    ("Electronics", "Speaker Battery", [
        ("Speaker", "Speaker Battery"),
        ("Smartwatch", "Smartwatch Battery"),
        ("Media Player", "Media Player Battery"),
        ("Game Console", "Game Console Battery"),
    ]),
    ("Business & Industrial", "Barcode Scanner Battery", [
        ("Barcode Scanner", "Barcode Scanner Battery"),
        ("Payment Terminal", "Payment Terminal Battery"),
        ("PDA & Pocket PC", "PDA, Pocket PC Battery"),
    ]),
    ("Shop All", "__SHOP_ALL__", []),
]

CREATE_MUT = """
mutation MenuCreate($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) {
  menuCreate(title: $title, handle: $handle, items: $items) {
    menu { id handle title }
    userErrors { field message }
  }
}
"""

ENUM_Q = '{ __type(name: "MenuItemType") { enumValues { name } } }'


def main() -> None:
    dry = "--dry" in sys.argv
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)

    # 1) 集合 title -> {handle, id}
    cols = c.request("GET", "smart_collections.json",
                     params={"limit": 250}).get("smart_collections", [])
    custom_cols = c.request("GET", "custom_collections.json",
                            params={"limit": 250}).get("custom_collections", [])
    col_of = {s["title"]: s for s in cols + custom_cols}
    print(f"[1] 集合 {len(col_of)} 个")

    def item_for(label: str, title: str) -> dict | None:
        """集合项=COLLECTION+resourceId；Shop All=HTTP 相对路径。"""
        if title == "__SHOP_ALL__":
            return {"title": label, "type": "HTTP", "url": "/collections/all"}
        s = col_of.get(title)
        if not s:
            return None
        return {"title": label, "type": "COLLECTION",
                "url": f"/collections/{s['handle']}",
                "resourceId": f"gid://shopify/Collection/{s['id']}"}

    # 2) 组装菜单树
    items = []
    missing = []
    for label, main_title, subs in GROUPS:
        node = item_for(label, main_title)
        if node is None:
            missing.append(main_title)
            node = {"title": label, "type": "HTTP", "url": "/collections/all"}
        children = []
        for sub_label, col_title in subs:
            ch = item_for(sub_label, col_title)
            if ch is None:
                missing.append(col_title)
                continue
            children.append(ch)
        if children:
            node["items"] = children
        items.append(node)

    print("[2] 菜单树:")
    for it in items:
        kids = it.get("items") or []
        print(f"  {it['title']:26} -> {it['url']} [{it['type']}]"
              + (f"  ({len(kids)} 子项)" if kids else ""))
    if missing:
        print(f"  !! 缺集合（跳过或降级）: {sorted(set(missing))}")

    if dry:
        print("(dry 模式结束)")
        return

    # 3) menuCreate（先校验 MenuItemType 枚举含需要的值）
    ev = (((c.graphql(ENUM_Q, {}) or {}).get("__type") or {})
          .get("enumValues") or [])
    vals = {v["name"] for v in ev}
    if ev and not {"COLLECTION", "HTTP"} <= vals:
        print(f"[3] !! MenuItemType 缺 COLLECTION/HTTP: {sorted(vals)}")
        return
    r = c.graphql(CREATE_MUT, {"title": "Main menu",
                               "handle": MENU_HANDLE, "items": items})
    node = (r.get("menuCreate") or {})
    errs = node.get("userErrors") or []
    print(f"[3] menuCreate: errs={errs} menu={node.get('menu')}")
    if errs:
        return

    # 4) Dawn header 绑定切换：sections/header-group.json 里 menu 引用
    a = c.request("GET", "assets.json",
                  params={"theme_id": THEME_ID,
                          "asset[key]": "sections/header-group.json"})
    asset = a.get("asset") or {}
    raw = asset.get("value") or ""
    if not raw:
        print("[4] !! header-group.json 不存在，列主题资产找 header")
        return
    import re as _re
    if '"estry-main-menu"' in raw:
        print("[4] 已绑定过，跳过")
        return
    new_raw = raw.replace('"main-menu"', f'"{MENU_HANDLE}"')
    if new_raw == raw:
        print("[4] !! 未找到 main-menu 引用，需人工检查资产")
        return
    c.request("PUT", f"themes/{THEME_ID}/assets.json",
              json_body={"asset": {"key": "sections/header-group.json",
                                   "value": new_raw}})
    print("[4] header 绑定已切换 main-menu -> estry-main-menu")

    # 5) 验证：拉回资产确认
    b = c.request("GET", "assets.json",
                  params={"theme_id": THEME_ID,
                          "asset[key]": "sections/header-group.json"})
    ok = f'"{MENU_HANDLE}"' in (b.get("asset") or {}).get("value", "")
    print(f"[5] 绑定验证: {'OK' if ok else 'FAIL'}")
    print("MENU-DONE（回滚：资产值换回 main-menu + 后台 Navigation 删除 estry-main-menu）")


if __name__ == "__main__":
    main()
