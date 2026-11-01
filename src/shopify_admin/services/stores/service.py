# -*- coding: utf-8 -*-
"""店铺与凭据服务：CRUD、客户端装配、连通性检测。

所有需要调用 Shopify API 的服务统一经 get_client() 装配凭据，
凭据只存在 stores 表，不散落在代码/配置中。
"""
from __future__ import annotations

from datetime import datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shopify_admin.core.database import session_scope
from shopify_admin.core.exceptions import NotFoundError, ShopifyAPIError
from shopify_admin.models.store import Store
from shopify_admin.platforms.shopify.client import ShopifyClient, StoreCredentials
from shopify_admin.platforms.shopify.types import VerifyResult


class StoreService:
    """店铺管理（同步风格，REST/MCP 共用）。"""

    # ------------------------------------------------------------------
    def list_stores(self, available_only: bool = False) -> list[dict]:
        with session_scope() as s:
            stmt = select(Store).order_by(Store.id)
            if available_only:
                stmt = stmt.where(Store.is_available.is_(True))
            stores = s.execute(stmt).scalars().all()
            return [self._to_dict(st) for st in stores]

    def get_store(self, store_id: int) -> dict:
        with session_scope() as s:
            st = s.get(Store, store_id)
            if st is None:
                raise NotFoundError(f"店铺不存在: {store_id}")
            return self._to_dict(st)

    def get_store_by_username(self, username: str) -> dict:
        with session_scope() as s:
            st = s.execute(select(Store).where(Store.username == username)).scalar_one_or_none()
            if st is None:
                raise NotFoundError(f"店铺不存在: {username}")
            return self._to_dict(st)

    def find_credentials_by_domain(self, domain: str) -> StoreCredentials | None:
        """按回调 shop 域名定位店铺凭据（webhook/carrier 验签用；未命中返回 None）。"""
        d = (domain or "").strip().lower()
        if not d:
            return None
        with session_scope() as s:
            st = s.execute(
                select(Store).where(
                    (func.lower(Store.domain) == d) | (func.lower(Store.primary_domain) == d)
                )
            ).scalar_one_or_none()
            if st is None:
                return None
            return StoreCredentials(api_key=st.api_key, api_secret=st.api_secret, domain=st.domain)

    # ------------------------------------------------------------------
    def create_store(
        self,
        username: str,
        api_key: str,
        api_secret: str = "",
        domain: str = "",
        **kwargs,
    ) -> dict:
        with session_scope() as s:
            st = Store(username=username, api_key=api_key, api_secret=api_secret, domain=domain, **kwargs)
            s.add(st)
            s.flush()
            return self._to_dict(st)

    def update_store(self, store_id: int, fields: dict) -> dict:
        allowed = {
            "api_key", "api_secret", "domain", "primary_domain", "is_available",
            "is_inventory_available", "rcustomerno", "main_ship_by", "ship_of_country_first",
        }
        with session_scope() as s:
            st = s.get(Store, store_id)
            if st is None:
                raise NotFoundError(f"店铺不存在: {store_id}")
            for k, v in fields.items():
                if k in allowed:
                    setattr(st, k, v)
            s.flush()
            return self._to_dict(st)

    # ------------------------------------------------------------------
    def get_client(self, store_id: int) -> ShopifyClient:
        """装配指定店铺的 Shopify 客户端。"""
        creds = self._load_credentials(store_id)
        return ShopifyClient(creds)

    def _load_credentials(self, store_id: int) -> StoreCredentials:
        with session_scope() as s:
            st = s.get(Store, store_id)
            if st is None:
                raise NotFoundError(f"店铺不存在: {store_id}")
            if not st.is_available:
                raise ShopifyAPIError(f"店铺已停用: {st.username}")
            return StoreCredentials(api_key=st.api_key, api_secret=st.api_secret, domain=st.domain)

    def verify(self, store_id: int) -> VerifyResult:
        """凭据连通性检测（GET shop.json），结果写回 last_verified_at。"""
        try:
            client = self.get_client(store_id)
            shop = client.verify()
            result = VerifyResult(
                store_id=store_id, ok=True,
                shop_name=shop.get("name", ""), domain=shop.get("myshopify_domain", ""),
                message="连通正常", checked_at=datetime.now(),
            )
        except Exception as e:
            result = VerifyResult(
                store_id=store_id, ok=False, message=str(e)[:300], checked_at=datetime.now(),
            )
        with session_scope() as s:
            st = s.get(Store, store_id)
            if st is not None:
                st.last_verified_at = result.checked_at
        logger.info(f"[stores] 凭据检测 store={store_id} ok={result.ok}: {result.message[:100]}")
        return result

    # ------------------------------------------------------------------
    @staticmethod
    def _to_dict(st: Store) -> dict:
        return {
            "id": st.id,
            "username": st.username,
            "domain": st.domain,
            "primary_domain": st.primary_domain,
            "is_available": st.is_available,
            "is_inventory_available": st.is_inventory_available,
            "rcustomerno": st.rcustomerno,
            "main_ship_by": st.main_ship_by,
            "ship_of_country_first": st.ship_of_country_first,
            "last_verified_at": st.last_verified_at.isoformat() if st.last_verified_at else None,
            "last_synced_at": st.last_synced_at.isoformat() if st.last_synced_at else None,
            # 凭据不回显明文
            "api_key_masked": (st.api_key[:4] + "****") if st.api_key else "",
        }
