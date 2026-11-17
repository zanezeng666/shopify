# -*- coding: utf-8 -*-
"""美国全免邮自动折扣 (价格已含运费, 前台撤掉三档收费的实际执行手段).

  背景: 店铺运费设置是 legacy 模式 (REST shipping_zones 可读, GraphQL 无写口),
  故用 Free Shipping 自动折扣实现美国前台全免邮 —— 与 Volume Tier 同体系,
  可逆可停; 原 zone 三档规则保留作兜底.
  2024-10 输入形态: destination.countries.add=[US] (注意是 add 不是 include),
  combinesWith.productDiscounts=true 保证与 Volume Tier 商品折扣并存.
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python add_free_shipping.py
"""
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client

TITLE = "Free US Shipping"

LIST_Q = """{
  discountNodes(first: 100, query: "status:active") {
    nodes {
      id
      discount {
        __typename
        ... on DiscountAutomaticFreeShipping { title status }
      }
    }
  }
}"""

CREATE_M = """mutation ($d: DiscountAutomaticFreeShippingInput!) {
  discountAutomaticFreeShippingCreate(freeShippingAutomaticDiscount: $d) {
    automaticDiscountNode { id }
    userErrors { field message }
  }
}"""

READBACK_Q = """{
  discountNodes(first: 100) {
    nodes {
      id
      discount {
        __typename
        ... on DiscountAutomaticFreeShipping {
          title status
          destinationSelection {
            __typename
            ... on DiscountCountries { countries }
            ... on DiscountCountryAll { allCountries }
          }
          combinesWith { productDiscounts orderDiscounts shippingDiscounts }
        }
      }
    }
  }
}"""


def main() -> None:
    # ---- 1. 查重 ----
    r = c.graphql(LIST_Q)
    exist = [n for n in r["discountNodes"]["nodes"]
             if (n["discount"].get("__typename") == "DiscountAutomaticFreeShipping"
                 and n["discount"].get("title") == TITLE)]
    if exist:
        print(f"[1] 已存在 '{TITLE}' x{len(exist)}, 幂等跳过创建")
    else:
        print(f"[1] 不存在, 创建: {TITLE}")
        payload = {
            "title": TITLE,
            "startsAt": datetime.now(timezone.utc).isoformat(),
            "destination": {"countries": {"add": ["US"]}},
            "combinesWith": {"productDiscounts": True, "orderDiscounts": True,
                             "shippingDiscounts": False},
        }
        r2 = c.graphql(CREATE_M, {"d": payload})
        errs = r2["discountAutomaticFreeShippingCreate"]["userErrors"]
        if errs:
            for e in errs:
                print(f"    !! userError: {e.get('field')}: {e.get('message')}")
            sys.exit(1)
        print(f"    created: {r2['discountAutomaticFreeShippingCreate']['automaticDiscountNode']['id']}")

    # ---- 2. readback ----
    r3 = c.graphql(READBACK_Q)
    found = [n for n in r3["discountNodes"]["nodes"]
             if n["discount"].get("__typename") == "DiscountAutomaticFreeShipping"]
    print(f"[2] readback: FreeShipping 折扣共 {len(found)} 个")
    for n in found:
        d = n["discount"]
        ds = d.get("destinationSelection") or {}
        cw = d.get("combinesWith") or {}
        tn = ds.get("__typename")
        if tn == "DiscountCountries":
            codes = list(ds.get("countries") or [])
        elif tn == "DiscountCountryAll":
            codes = ["ALL"] if ds.get("allCountries") else []
        else:
            codes = []
        print(f"    '{d['title']}' {d['status']} destination={codes}"
              f" combinesWith(product={cw.get('productDiscounts')} order={cw.get('orderDiscounts')})")
        ok = (d["title"] == TITLE and d["status"] == "ACTIVE" and "US" in codes)
        print(f"    -> {'PASS' if ok else 'CHECK'}")
    print("[3] 注: 原 zone 三档规则保留作兜底; 停用=后台下架该折扣即恢复收费")


if __name__ == "__main__":
    main()
