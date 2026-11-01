# -*- coding: utf-8 -*-
"""产品服务：同步 / 查询 / 改价 / SEO / Collections / Metafields。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import func, select

from shopify_admin.core.database import session_scope
from shopify_admin.core.exceptions import NotFoundError
from shopify_admin.models.product import Collection, Product, ProductCollection, ProductVariant
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.platforms.shopify.types import ProductSyncResult
from shopify_admin.services.stores.service import StoreService

_MAX_PAGES = 40


def _to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


class ProductService:
    def __init__(self, store_service: StoreService | None = None):
        self._stores = store_service or StoreService()

    # ------------------------------------------------------------------
    def sync_products(
        self,
        store_id: int,
        updated_at_min: str | None = None,
        max_pages: int = _MAX_PAGES,
    ) -> ProductSyncResult:
        """同步产品+变体（upsert）。默认增量（游标=库内 max(shopify_updated_at) 回退 5 分钟）。"""
        client = self._stores.get_client(store_id)
        rest = ShopifyRest(client)

        if updated_at_min is None:
            with session_scope() as s:
                last = s.execute(
                    select(func.max(Product.shopify_updated_at)).where(Product.store_id == store_id)
                ).scalar()
            if last is not None:
                updated_at_min = (last - __import__("datetime").timedelta(minutes=5)).strftime(
                    "%Y-%m-%dT%H:%M:%S+00:00"
                )

        fetched = created_n = updated_n = 0
        since_id: int | None = None
        for _ in range(max_pages):
            products = rest.products(since_id=since_id, updated_at_min=updated_at_min)
            if not products:
                break
            for p in products:
                c, u = self._upsert_product(store_id, p)
                fetched += 1
                created_n += c
                updated_n += u
            if len(products) < 250:
                break
            since_id = products[-1]["id"]

        result = ProductSyncResult(store_id=store_id, fetched=fetched, created=created_n, updated=updated_n)
        logger.info(f"[products] 同步完成 {result.model_dump()}")
        client.close()
        return result

    def _upsert_product(self, store_id: int, p: dict) -> tuple[int, int]:
        with session_scope() as s:
            prod = s.execute(
                select(Product).where(Product.store_id == store_id, Product.shopify_product_id == p["id"])
            ).scalar_one_or_none()
            is_new = prod is None
            if is_new:
                prod = Product(store_id=store_id, shopify_product_id=p["id"])
                s.add(prod)
            self._apply_fields(prod, p)
            s.flush()
            self._upsert_variants(s, store_id, prod, p.get("variants", []))
            return (1, 0) if is_new else (0, 1)

    @staticmethod
    def _apply_fields(prod: Product, p: dict) -> None:
        prod.title = p.get("title") or ""
        prod.handle = p.get("handle") or ""
        prod.vendor = p.get("vendor") or ""
        prod.product_type = p.get("product_type") or ""
        prod.status = p.get("status") or ""
        prod.tags = p.get("tags") or ""
        prod.published_at = _to_dt(p.get("published_at"))
        prod.shopify_created_at = _to_dt(p.get("created_at"))
        prod.shopify_updated_at = _to_dt(p.get("updated_at"))
        prod.raw = p

    @staticmethod
    def _upsert_variants(s, store_id: int, prod: Product, variants: list[dict]) -> None:
        for v in variants:
            var = s.execute(
                select(ProductVariant).where(
                    ProductVariant.store_id == store_id, ProductVariant.shopify_variant_id == v["id"]
                )
            ).scalar_one_or_none()
            if var is None:
                var = ProductVariant(store_id=store_id, shopify_variant_id=v["id"])
                s.add(var)
            var.product_id = prod.id
            var.shopify_product_id = prod.shopify_product_id
            var.inventory_item_id = v.get("inventory_item_id")
            var.title = v.get("title") or ""
            var.sku = v.get("sku") or ""
            var.barcode = v.get("barcode") or ""
            var.option1 = v.get("option1") or ""
            var.option2 = v.get("option2") or ""
            var.option3 = v.get("option3") or ""
            var.price = _dec(v.get("price"))
            var.compare_at_price = _dec(v.get("compare_at_price"))
            var.grams = v.get("grams") or 0
            var.shopify_updated_at = _to_dt(v.get("updated_at"))

    # ------------------------------------------------------------------
    def list_products(
        self,
        store_id: int | None = None,
        title_like: str | None = None,
        handle: str | None = None,
        sku: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        with session_scope() as s:
            stmt = select(Product)
            count_stmt = select(func.count(Product.id))
            if store_id:
                stmt = stmt.where(Product.store_id == store_id)
                count_stmt = count_stmt.where(Product.store_id == store_id)
            if title_like:
                stmt = stmt.where(Product.title.like(f"%{title_like}%"))
                count_stmt = count_stmt.where(Product.title.like(f"%{title_like}%"))
            if handle:
                stmt = stmt.where(Product.handle == handle)
                count_stmt = count_stmt.where(Product.handle == handle)
            if status:
                stmt = stmt.where(Product.status == status)
                count_stmt = count_stmt.where(Product.status == status)

            total = s.execute(count_stmt).scalar() or 0
            prods = (
                s.execute(stmt.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size))
                .scalars()
                .all()
            )
            items = []
            for p in prods:
                variants = s.execute(
                    select(ProductVariant).where(ProductVariant.product_id == p.id)
                ).scalars().all()
                items.append(self._prod_dict(p, variants))
            return {"total": total, "page": page, "page_size": page_size, "items": items}

    def get_product(self, product_id: int) -> dict:
        with session_scope() as s:
            p = s.get(Product, product_id)
            if p is None:
                raise NotFoundError(f"产品不存在: {product_id}")
            variants = s.execute(select(ProductVariant).where(ProductVariant.product_id == p.id)).scalars().all()
            return self._prod_dict(p, variants)

    # ------------------------------------------------------------------
    def update_variant_price(self, store_id: int, variant_id: int, price: str | float) -> dict:
        """改价（Shopify 远端 + 本地同步）。variant_id 为 Shopify 变体 ID。"""
        client = self._stores.get_client(store_id)
        try:
            updated = ShopifyRest(client).set_variant_price(variant_id, price)
            self._upsert_product(store_id, {"id": updated.get("product_id"), "variants": [updated]})
            return {"variant_id": variant_id, "price": str(price), "ok": True}
        finally:
            client.close()

    def batch_update_prices(self, store_id: int, prices: dict[int, str | float]) -> list[dict]:
        """批量改价：{shopify_variant_id: price}。逐个执行，失败项标记。"""
        results = []
        for vid, price in prices.items():
            try:
                results.append(self.update_variant_price(store_id, vid, price))
            except Exception as e:
                results.append({"variant_id": vid, "price": str(price), "ok": False, "error": str(e)[:200]})
        return results

    def update_product_seo(
        self,
        store_id: int,
        product_id: int,
        title: str | None = None,
        seo_title: str | None = None,
        seo_description: str | None = None,
        tags: str | None = None,
    ) -> dict:
        client = self._stores.get_client(store_id)
        try:
            fields: dict[str, Any] = {}
            if title is not None:
                fields["title"] = title
            if seo_title is not None:
                fields["metafields_global_title_tag"] = seo_title
            if seo_description is not None:
                fields["metafields_global_description_tag"] = seo_description
            if tags is not None:
                fields["tags"] = tags
            updated = ShopifyRest(client).update_product(product_id, fields)
            with session_scope() as s:
                p = s.execute(
                    select(Product).where(Product.store_id == store_id, Product.shopify_product_id == product_id)
                ).scalar_one_or_none()
                if p:
                    if title is not None:
                        p.title = title
                    if tags is not None:
                        p.tags = tags
                    p.seo_title = seo_title or p.seo_title
                    p.seo_description = seo_description or p.seo_description
            return {"product_id": product_id, "updated": list(fields.keys()), "ok": True}
        finally:
            client.close()

    # ------------------------------------------------------------------
    def sync_collections(self, store_id: int) -> dict:
        """同步手动集合 + 智能集合及其产品归属。"""
        client = self._stores.get_client(store_id)
        rest = ShopifyRest(client)
        try:
            n_created = n_updated = n_links = 0
            for fetch, is_smart in ((rest.custom_collections, False), (rest.smart_collections, True)):
                page = 0
                while page < 20:
                    cols = fetch(page_info=None)
                    if not cols:
                        break
                    for c in cols:
                        with session_scope() as s:
                            col = s.execute(
                                select(Collection).where(
                                    Collection.store_id == store_id,
                                    Collection.shopify_collection_id == c["id"],
                                )
                            ).scalar_one_or_none()
                            if col is None:
                                col = Collection(store_id=store_id, shopify_collection_id=c["id"])
                                s.add(col)
                                n_created += 1
                            else:
                                n_updated += 1
                            col.title = c.get("title") or ""
                            col.handle = c.get("handle") or ""
                            col.is_smart = is_smart
                            col.published_at = _to_dt(c.get("published_at"))
                            col.shopify_updated_at = _to_dt(c.get("updated_at"))
                            col.raw = c
                            s.flush()
                            # 手动集合拉产品归属
                            if not is_smart:
                                for collect in rest.collect_products(c["id"]):
                                    prod = s.execute(
                                        select(Product).where(
                                            Product.store_id == store_id,
                                            Product.shopify_product_id == collect.get("product_id"),
                                        )
                                    ).scalar_one_or_none()
                                    if prod is not None:
                                        link = s.execute(
                                            select(ProductCollection).where(
                                                ProductCollection.product_id == prod.id,
                                                ProductCollection.collection_id == col.id,
                                            )
                                        ).scalar_one_or_none()
                                        if link is None:
                                            s.add(ProductCollection(product_id=prod.id, collection_id=col.id))
                                            n_links += 1
                    if len(cols) < 250:
                        break
                    page += 1
            return {"created": n_created, "updated": n_updated, "links": n_links}
        finally:
            client.close()

    # ------------------------------------------------------------------
    @staticmethod
    def _prod_dict(p: Product, variants: list[ProductVariant]) -> dict:
        return {
            "id": p.id,
            "store_id": p.store_id,
            "shopify_product_id": p.shopify_product_id,
            "title": p.title,
            "handle": p.handle,
            "vendor": p.vendor,
            "product_type": p.product_type,
            "status": p.status,
            "tags": p.tags,
            "shopify_updated_at": p.shopify_updated_at.isoformat() if p.shopify_updated_at else None,
            "variants": [
                {
                    "id": v.id,
                    "shopify_variant_id": v.shopify_variant_id,
                    "title": v.title,
                    "sku": v.sku,
                    "barcode": v.barcode,
                    "price": float(v.price) if v.price is not None else None,
                    "compare_at_price": float(v.compare_at_price) if v.compare_at_price is not None else None,
                    "grams": v.grams,
                    "inventory_item_id": v.inventory_item_id,
                }
                for v in variants
            ],
        }
