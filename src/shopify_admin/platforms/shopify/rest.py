# -*- coding: utf-8 -*-
"""Shopify REST Admin API 资源封装。

只做协议层（参数组装 + 响应透传），业务逻辑在 services 层。
全部返回原始 dict / list，入库解析由 service 负责。
"""
from __future__ import annotations

from typing import Any

from shopify_admin.platforms.shopify.client import ShopifyClient


class ShopifyRest:
    """按资源分组的 REST 端点。"""

    def __init__(self, client: ShopifyClient):
        self.client = client

    # ---- shop ----
    def shop(self) -> dict[str, Any]:
        return self.client.request("GET", "shop.json").get("shop", {})

    # ---- orders ----
    def orders(
        self,
        created_at_min: str | None = None,
        updated_at_min: str | None = None,
        status: str = "any",
        limit: int = 250,
        page_info: str | None = None,
        since_id: int | None = None,
        financial_status: str | None = None,
        fulfillment_status: str | None = None,
    ) -> list[dict[str, Any]]:
        """拉取订单列表（分页用 page_info，由调用方循环取 next）。"""
        params: dict[str, Any] = {"limit": min(limit, 250), "status": status}
        for k, v in {
            "created_at_min": created_at_min,
            "updated_at_min": updated_at_min,
            "page_info": page_info,
            "since_id": since_id,
            "financial_status": financial_status,
            "fulfillment_status": fulfillment_status,
        }.items():
            if v is not None and v != "":
                params[k] = v
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}  # page_info 必须单独携带
        return self.client.request("GET", "orders.json", params=params).get("orders", [])

    def order(self, order_id: int) -> dict[str, Any]:
        return self.client.request("GET", f"orders/{order_id}.json").get("order", {})

    def close_order(self, order_id: int) -> dict[str, Any]:
        return self.client.request("POST", f"orders/{order_id}/close.json").get("order", {})

    def cancel_order(self, order_id: int) -> dict[str, Any]:
        return self.client.request("POST", f"orders/{order_id}/cancel.json").get("order", {})

    # ---- products / variants ----
    def products(
        self,
        limit: int = 250,
        page_info: str | None = None,
        since_id: int | None = None,
        updated_at_min: str | None = None,
        published_status: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": min(limit, 250)}
        for k, v in {
            "page_info": page_info,
            "since_id": since_id,
            "updated_at_min": updated_at_min,
            "published_status": published_status,
        }.items():
            if v is not None and v != "":
                params[k] = v
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}
        return self.client.request("GET", "products.json", params=params).get("products", [])

    def product(self, product_id: int) -> dict[str, Any]:
        return self.client.request("GET", f"products/{product_id}.json").get("product", {})

    def create_product(self, product: dict[str, Any]) -> dict[str, Any]:
        """创建产品（含 variants）。product 结构对齐 REST products.json。"""
        return self.client.request("POST", "products.json", json_body={"product": product}).get(
            "product", {}
        )

    def product_by_handle(self, handle: str) -> dict[str, Any] | None:
        """按 handle 查产品（不存在返回 None）——新品发布幂等防重建。"""
        rsp = self.client.request("GET", "products.json", params={"handle": handle, "limit": 1})
        prods = rsp.get("products", [])
        return prods[0] if prods else None

    def update_product(self, product_id: int, product: dict[str, Any]) -> dict[str, Any]:
        """更新产品字段（title/body_html/tags/SEO/variants 等）。"""
        return self.client.request("PUT", f"products/{product_id}.json", json_body={"product": product}).get(
            "product", {}
        )

    def update_variant(self, variant_id: int, variant: dict[str, Any]) -> dict[str, Any]:
        """更新变体（price/compare_at_price/sku/barcode/weight 等）。"""
        return self.client.request("PUT", f"variants/{variant_id}.json", json_body={"variant": variant}).get(
            "variant", {}
        )

    def set_variant_price(self, variant_id: int, price: str | float) -> dict[str, Any]:
        return self.update_variant(variant_id, {"price": str(price), "price_set": None})

    def count_products(self) -> int:
        return self.client.request("GET", "products/count.json").get("count", 0)

    # ---- collections ----
    def custom_collections(self, limit: int = 250, page_info: str | None = None) -> list[dict[str, Any]]:
        params = {"limit": min(limit, 250)}
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}
        return self.client.request("GET", "custom_collections.json", params=params).get("custom_collections", [])

    def smart_collections(self, limit: int = 250, page_info: str | None = None) -> list[dict[str, Any]]:
        params = {"limit": min(limit, 250)}
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}
        return self.client.request("GET", "smart_collections.json", params=params).get("smart_collections", [])

    def collect_products(self, collection_id: int, limit: int = 250) -> list[dict[str, Any]]:
        return self.client.request(
            "GET", "collects.json", params={"collection_id": collection_id, "limit": min(limit, 250)}
        ).get("collects", [])

    # ---- locations / inventory ----
    def locations(self) -> list[dict[str, Any]]:
        return self.client.request("GET", "locations.json").get("locations", [])

    def inventory_levels(self, location_ids: list[int] | None = None, limit: int = 250) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": min(limit, 250)}
        if location_ids:
            params["location_ids"] = ",".join(str(i) for i in location_ids)
        return self.client.request("GET", "inventory_levels.json", params=params).get("inventory_levels", [])

    def set_inventory_level(
        self,
        inventory_item_id: int,
        location_id: int,
        available: int,
        disconnect_if_necessary: bool = False,
    ) -> dict[str, Any]:
        """设置位置库存（绝对值）。"""
        return self.client.request(
            "POST",
            "inventory_levels/set.json",
            json_body={
                "inventory_item_id": inventory_item_id,
                "location_id": location_id,
                "available": available,
                "disconnect_if_necessary": disconnect_if_necessary,
            },
        )

    def adjust_inventory_level(self, inventory_item_id: int, location_id: int, adjustment: int) -> dict[str, Any]:
        return self.client.request(
            "POST",
            "inventory_levels/adjust.json",
            json_body={
                "inventory_item_id": inventory_item_id,
                "location_id": location_id,
                "available_adjustment": adjustment,
            },
        )

    def inventory_items(self, ids: list[int]) -> list[dict[str, Any]]:
        return self.client.request(
            "GET", "inventory_items.json", params={"ids": ",".join(str(i) for i in ids)}
        ).get("inventory_items", [])

    # ---- fulfillment ----
    def fulfillments(self, order_id: int) -> list[dict[str, Any]]:
        return self.client.request("GET", f"orders/{order_id}/fulfillments.json").get("fulfillments", [])

    def create_fulfillment(
        self,
        order_id: int,
        tracking_number: str,
        tracking_company: str = "",
        tracking_url: str = "",
        line_items: list[dict[str, int]] | None = None,
        notify_customer: bool = True,
    ) -> dict[str, Any]:
        """跟踪号回传：为订单创建 fulfillment（可指定行项，空=全部）。"""
        body: dict[str, Any] = {
            "fulfillment": {
                "tracking_info": {
                    "number": tracking_number,
                    "company": tracking_company,
                    "url": tracking_url,
                },
                "notify_customer": notify_customer,
            }
        }
        if line_items:
            body["fulfillment"]["line_items"] = line_items
        return self.client.request("POST", f"orders/{order_id}/fulfillments.json", json_body=body).get(
            "fulfillment", {}
        )

    def create_fulfillment_event(
        self, order_id: int, fulfillment_id: int, status: str = "in_transit"
    ) -> dict[str, Any]:
        return self.client.request(
            "POST",
            f"orders/{order_id}/fulfillments/{fulfillment_id}/events.json",
            json_body={"event": {"status": status}},
        ).get("fulfillment_event", {})

    # ---- finance ----
    def payouts(self, limit: int = 250, page_info: str | None = None) -> list[dict[str, Any]]:
        params = {"limit": min(limit, 250)}
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}
        return self.client.request("GET", "shopify_payments/payouts.json", params=params).get("payouts", [])

    def transactions(self, order_id: int) -> list[dict[str, Any]]:
        return self.client.request("GET", f"orders/{order_id}/transactions.json").get("transactions", [])

    def all_transactions(
        self, since_id: int | None = None, limit: int = 250, page_info: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": min(limit, 250)}
        if since_id:
            params["since_id"] = since_id
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}
        return self.client.request("GET", "shopify_payments/transactions.json", params=params).get(
            "transactions", []
        )

    # ---- metafields ----
    def metafields(self, owner_resource: str, owner_id: int) -> list[dict[str, Any]]:
        return self.client.request("GET", f"{owner_resource}/{owner_id}/metafields.json").get("metafields", [])

    def update_metafield(
        self, owner_resource: str, owner_id: int, namespace: str, key: str, value: str, value_type: str = "string"
    ) -> dict[str, Any]:
        return self.client.request(
            "POST",
            f"{owner_resource}/{owner_id}/metafields.json",
            json_body={
                "metafield": {
                    "namespace": namespace,
                    "key": key,
                    "value": value,
                    "type": _metafield_type(value_type),
                }
            },
        ).get("metafield", {})

    # ---- carrier services（承运商实时运费，结账回调由 services/shipping 提供）----
    def list_carrier_services(self) -> list[dict[str, Any]]:
        return self.client.request("GET", "carrier_services.json").get("carrier_services", [])

    def create_carrier_service(self, carrier_service: dict[str, Any]) -> dict[str, Any]:
        return self.client.request(
            "POST", "carrier_services.json", json_body={"carrier_service": carrier_service}
        ).get("carrier_service", {})

    def delete_carrier_service(self, service_id: int) -> bool:
        self.client.request("DELETE", f"carrier_services/{service_id}.json")
        return True


def _metafield_type(value_type: str) -> str:
    """旧 value_type（string/json_string/integer/float）映射到新 type。"""
    return {
        "string": "single_line_text_field",
        "json_string": "json",
        "integer": "number_integer",
        "float": "number_decimal",
    }.get(value_type, value_type)
