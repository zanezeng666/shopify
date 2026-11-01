# -*- coding: utf-8 -*-
"""产品域：产品 / 变体 / 集合 / Metafields。

设计要点：
- 保留 Shopify 原生 ID（BIGINT）作为业务键（store 范围内唯一）
- shopify_updated_at 作为增量同步游标
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, DateTime, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from shopify_admin.models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("store_id", "shopify_product_id", name="uq_products_store_spid"),
        Index("ix_products_store_updated", "store_id", "shopify_updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    shopify_product_id: Mapped[int] = mapped_column(BigInteger, comment="Shopify 产品 ID")
    title: Mapped[str] = mapped_column(String(512), default="")
    handle: Mapped[str] = mapped_column(String(255), default="", index=True)
    vendor: Mapped[str] = mapped_column(String(255), default="")
    product_type: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="", comment="active/draft/archived")
    tags: Mapped[str] = mapped_column(Text, default="")
    seo_title: Mapped[str] = mapped_column(String(512), default="")
    seo_description: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    shopify_created_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    shopify_updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment="增量同步游标")
    raw: Mapped[dict | None] = mapped_column(JSON, default=None, comment="Shopify 原始 JSON")


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("store_id", "shopify_variant_id", name="uq_variants_store_svid"),
        Index("ix_variants_store_spu", "store_id", "shopify_product_id"),
        Index("ix_variants_sku", "sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    shopify_variant_id: Mapped[int] = mapped_column(BigInteger, comment="Shopify 变体 ID")
    shopify_product_id: Mapped[int] = mapped_column(BigInteger, comment="冗余：Shopify 产品 ID")
    inventory_item_id: Mapped[int | None] = mapped_column(BigInteger, default=None, comment="库存项 ID")
    title: Mapped[str] = mapped_column(String(512), default="")
    sku: Mapped[str] = mapped_column(String(128), default="", comment="SKU（对应 CS/海外仓商品映射键）")
    barcode: Mapped[str] = mapped_column(String(64), default="")
    option1: Mapped[str] = mapped_column(String(255), default="")
    option2: Mapped[str] = mapped_column(String(255), default="")
    option3: Mapped[str] = mapped_column(String(255), default="")
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    compare_at_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    grams: Mapped[int] = mapped_column(Integer, default=0)
    shopify_updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    raw: Mapped[dict | None] = mapped_column(JSON, default=None)


class Collection(Base, TimestampMixin):
    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("store_id", "shopify_collection_id", name="uq_collections_store_scid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    shopify_collection_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(512), default="")
    handle: Mapped[str] = mapped_column(String(255), default="", index=True)
    is_smart: Mapped[bool] = mapped_column(default=False, comment="智能集合(true)/手动集合(false)")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    shopify_updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    raw: Mapped[dict | None] = mapped_column(JSON, default=None)


class ProductCollection(Base):
    """产品-集合关联（手动集合成员 / 智能集合同步结果）。"""

    __tablename__ = "product_collections"
    __table_args__ = (
        UniqueConstraint("product_id", "collection_id", name="uq_pc_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), index=True)


class Metafield(Base, TimestampMixin):
    __tablename__ = "metafields"
    __table_args__ = (
        UniqueConstraint("store_id", "owner_resource", "owner_id", "namespace", "key", name="uq_metafields_owner"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    owner_resource: Mapped[str] = mapped_column(String(32), comment="product/variant/collection/order")
    owner_id: Mapped[int] = mapped_column(BigInteger, comment="Shopify 资源 ID")
    namespace: Mapped[str] = mapped_column(String(128))
    key: Mapped[str] = mapped_column(String(128))
    value: Mapped[str] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(16), default="string", comment="string/json_string/integer...")
    shopify_updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
