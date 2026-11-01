# -*- coding: utf-8 -*-
"""营销域：GMC Feed / Google 商品字段。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from shopify_admin.models.base import Base, TimestampMixin


class GoogleProductField(Base, TimestampMixin):
    """Google Shopping 商品级覆盖字段（GMC feed 数据源之一）。

    迁移自老库 shopify.google_metafields / gmc_feed 相关数据。
    """

    __tablename__ = "google_product_fields"
    __table_args__ = (
        UniqueConstraint("store_id", "shopify_product_id", name="uq_gpf_store_spu"),
        Index("ix_gpf_store_mpn", "store_id", "mpn"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    shopify_product_id: Mapped[int] = mapped_column(BigInteger)
    shopify_variant_id: Mapped[int | None] = mapped_column(BigInteger, default=None, comment="空=产品级，非空=变体级覆盖")
    mpn: Mapped[str] = mapped_column(String(128), default="", comment="制造商部件号（对应 CS 型号）")
    brand: Mapped[str] = mapped_column(String(255), default="")
    gtin: Mapped[str] = mapped_column(String(64), default="")
    google_product_category: Mapped[str] = mapped_column(String(255), default="")
    condition: Mapped[str] = mapped_column(String(32), default="new")
    custom_label0: Mapped[str] = mapped_column(String(128), default="")
    custom_label1: Mapped[str] = mapped_column(String(128), default="")
    custom_label2: Mapped[str] = mapped_column(String(128), default="")
    custom_label3: Mapped[str] = mapped_column(String(128), default="")
    custom_label4: Mapped[str] = mapped_column(String(128), default="")


class GmcFeed(Base, TimestampMixin):
    """GMC Feed 生成记录。"""

    __tablename__ = "gmc_feeds"
    __table_args__ = (Index("ix_gmc_feeds_store_time", "store_id", "generated_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    feed_file: Mapped[str] = mapped_column(String(512), default="", comment="生成的 feed 文件路径")
    product_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="generated", comment="generated/uploaded/failed")
    settings: Mapped[dict | None] = mapped_column(JSON, default=None, comment="生成参数（国家/币种/过滤条件）")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
