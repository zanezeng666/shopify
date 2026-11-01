# -*- coding: utf-8 -*-
"""店铺与凭据。修正老表缺陷：自增 id 主键，api_key 降为唯一索引。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shopify_admin.models.base import Base, TimestampMixin


class Store(Base, TimestampMixin):
    """Shopify 店铺（凭据集中管理）。迁移自老库 shopify.shopify_store_info。"""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, comment="店铺账号名（操作归属）")
    api_key: Mapped[str] = mapped_column(String(255), unique=True, comment="Shopify API Key / Admin API access token")
    api_secret: Mapped[str] = mapped_column(String(255), default="", comment="API Secret / 密码")
    domain: Mapped[str] = mapped_column(String(255), default="", comment="myshopify.com 域名")
    primary_domain: Mapped[str] = mapped_column(String(255), default="", comment="主域名（自定义域名）")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, comment="店铺可用状态")
    is_inventory_available: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否参与库存同步")
    rcustomerno: Mapped[int | None] = mapped_column(BigInteger, default=None, comment="CS 供应商客户号")
    main_ship_by: Mapped[str] = mapped_column(String(32), default="", comment="主发货方式（cs/fastrite/auto）")
    ship_of_country_first: Mapped[str] = mapped_column(String(8), default="", comment="优先发货国家代号")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment="凭据最近连通性检测时间")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment="最近一次全量同步时间")
