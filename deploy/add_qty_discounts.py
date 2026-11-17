# -*- coding: utf-8 -*-
"""Estry 数量阶梯自动折扣 (10+/20+/50+/100+ 件 -> 5%/6%/8%/10%).

  Shopify 自动折扣(quantity 门槛)只能走 GraphQL Admin API:
  discountAutomaticBasicCreate + customerBuys.value.quantity + customerGets.value.percentage.
  ★降序创建 (100->50->20->10): 订单只应用一个自动折扣, 若 Shopify 按"首个符合"而非
  "最优"选择, 先创建的高档优先命中, 两种语义下高档客户都拿到高档折扣.
  幂等: 按 title 前缀查现有 Volume Tier 折扣, 参数一致跳过 / 不一致删了重建.
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python add_qty_discounts.py
"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client

# (min_qty, pct) —— 降序
TIERS = [(100, 10.0), (50, 8.0), (20, 6.0), (10, 5.0)]
PREFIX = "Volume Tier"

LIST_Q = """{
  discountNodes(first: 100) {
    nodes {
      id
      discount {
        __typename
        ... on DiscountAutomaticBasic {
          title
          status
          minimumRequirement {
            ... on DiscountMinimumQuantity { greaterThanOrEqualToQuantity }
          }
          customerGets {
            value { ... on DiscountPercentage { percentage } }
          }
        }
      }
    }
  }
}"""

CREATE_M = """mutation ($d: DiscountAutomaticBasicInput!) {
  discountAutomaticBasicCreate(automaticBasicDiscount: $d) {
    automaticDiscountNode { id }
    userErrors { field message }
  }
}"""

DELETE_M = """mutation ($id: ID!) {
  discountNodeDelete(id: $id) {
    deletedDiscountNodeId
    userErrors { field message }
  }
}"""


def tier_title(qty: int, pct: float) -> str:
    p = f"{pct:g}"
    return f"{PREFIX} {qty}+ pcs (-{p}%)"


def list_volume_nodes() -> dict:
    """现有 Volume Tier 自动折扣: title -> {id, min_qty, pct, status}."""
    data = c.graphql(LIST_Q)
    out = {}
    for n in data["discountNodes"]["nodes"]:
        d = n.get("discount") or {}
        if d.get("__typename") != "DiscountAutomaticBasic":
            continue
        if not (d.get("title") or "").startswith(PREFIX):
            continue
        out[d["title"]] = {
            "id": n["id"],
            "min_qty": (d.get("minimumRequirement") or {}).get("greaterThanOrEqualToQuantity"),
            "pct": (d.get("customerGets", {}).get("value") or {}).get("percentage"),
            "status": d.get("status"),
        }
    return out


def _raise_user_errors(tag: str, ues: list) -> None:
    if ues:
        msgs = "; ".join(f"{u.get('field')}: {u.get('message')}" for u in ues)
        raise RuntimeError(f"{tag} userErrors: {msgs}")


def manual_guide() -> None:
    print("    后台手动 (Discounts -> Create -> Amount off products -> Automatic):")
    for qty, pct in sorted(TIERS, reverse=True):
        print(f"      title='Volume Tier {qty}+ pcs'  Minimum quantity={qty}  Percentage={pct:g}%  无结束日期")
    print("    创建后重跑本脚本做参数核对.")


def main() -> None:
    # ---- 0. 权限预检: scope 端点仅 OAuth token 形态开放, Basic Auth 下 404;
    #     故 scope 尽力而为, 真正判据=GraphQL discountNodes 实探 ----
    try:
        scopes = {s["handle"] for s in c.request("GET", "oauth/access_scopes.json").get("access_scopes", [])}
        print(f"[0] scopes: {sorted(scopes)}")
        if not {"read_discounts", "write_discounts"} <= scopes:
            print("[0] !! token 缺 read/write_discounts, 无法经 API 创建.")
            manual_guide()
            return
    except Exception as e:  # noqa: BLE001
        print(f"[0] scope 端点不可用 ({type(e).__name__}), 改用 GraphQL 实探判断权限")
    try:
        c.graphql("{ discountNodes(first: 1) { nodes { id } } }")
    except Exception as e:  # noqa: BLE001
        print(f"[0] !! GraphQL discountNodes 无权限: {e}")
        manual_guide()
        return

    # ---- 1. 现有折扣对账 ----
    existing = list_volume_nodes()
    print(f"[1] 现有 {PREFIX}* 自动折扣: {len(existing)}")
    wanted = {tier_title(q, p): (q, p) for q, p in TIERS}

    # 1a. 清掉不在目标清单里的旧 Volume Tier (如改档位后的残留)
    for title, node in existing.items():
        if title not in wanted:
            r = c.graphql(DELETE_M, {"id": node["id"]})
            _raise_user_errors(f"delete {title}", r["discountNodeDelete"]["userErrors"])
            print(f"    delete 过期档位 {title} OK")

    # ---- 2. 降序创建/核对 (100 -> 10) ----
    for qty, pct in sorted(TIERS, reverse=True):
        title = tier_title(qty, pct)
        node = existing.get(title)
        if node:
            ok_q = node["min_qty"] is not None and int(node["min_qty"]) == qty
            ok_p = node["pct"] is not None and abs(float(node["pct"]) * 100 - pct) < 1e-6
            if ok_q and ok_p:
                print(f"[2] {title}: 已存在且参数一致 (status={node['status']}), 跳过")
                continue
            print(f"[2] {title}: 参数不一致 (min_qty={node['min_qty']} pct={node['pct']}), 删除重建")
            r = c.graphql(DELETE_M, {"id": node["id"]})
            _raise_user_errors(f"delete {title}", r["discountNodeDelete"]["userErrors"])
        payload = {
            "title": title,
            "startsAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "minimumRequirement": {"quantity": {"greaterThanOrEqualToQuantity": str(qty)}},
            "customerGets": {"items": {"all": True}, "value": {"percentage": pct / 100.0}},
        }
        r = c.graphql(CREATE_M, {"d": payload})
        _raise_user_errors(f"create {title}", r["discountAutomaticBasicCreate"]["userErrors"])
        print(f"[2] {title}: created {r['discountAutomaticBasicCreate']['automaticDiscountNode']['id']}")

    # ---- 3. readback 复核 (含 percentage 语义: 10 应原样回读 10 而非 0.1) ----
    time.sleep(2)
    final = list_volume_nodes()
    assert len(final) == len(TIERS), f"expect {len(TIERS)} tiers, got {len(final)}: {list(final)}"
    for qty, pct in sorted(TIERS, reverse=True):
        title = tier_title(qty, pct)
        node = final[title]
        assert node["min_qty"] is not None and int(node["min_qty"]) == qty, f"{title} min_qty={node['min_qty']}"
        got_pct = float(node["pct"]) * 100  # percentage 读侧同为 0-1 小数
        assert abs(got_pct - pct) < 1e-6, f"{title} percentage readback={got_pct}% != {pct}% (语义漂移!)"
        print(f"[3] {title}: qty>={qty} -{got_pct:g}% status={node['status']} OK")
    print("ADD-QTY-DISCOUNTS-DONE")


if __name__ == "__main__":
    main()
