# -*- coding: utf-8 -*-
"""营销服务：Google 商品字段维护 + GMC Feed 生成（TSV）。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from loguru import logger
from sqlalchemy import func, select

from shopify_admin.core.database import session_scope
from shopify_admin.models.marketing import GmcFeed, GoogleProductField
from shopify_admin.models.product import Product, ProductVariant
from shopify_admin.models.store import Store

_FEED_DIR = Path("output/gmc_feeds")

# GMC TSV 必需列
_GMC_COLUMNS = [
    "id", "title", "description", "link", "image_link", "availability",
    "price", "brand", "mpn", "condition", "google_product_category",
    "custom_label0", "custom_label1", "custom_label2", "custom_label3", "custom_label4",
]


class MarketingService:
    # ------------------------------------------------------------------
    # Google 商品字段
    # ------------------------------------------------------------------
    def list_google_fields(self, store_id: int, mpn_like: str | None = None) -> list[dict]:
        with session_scope() as s:
            stmt = select(GoogleProductField).where(GoogleProductField.store_id == store_id)
            if mpn_like:
                stmt = stmt.where(GoogleProductField.mpn.like(f"%{mpn_like}%"))
            rows = s.execute(stmt.order_by(GoogleProductField.id.desc())).scalars().all()
            return [self._gpf_dict(r) for r in rows]

    def upsert_google_field(
        self, store_id: int, shopify_product_id: int, shopify_variant_id: int | None = None, **kwargs
    ) -> dict:
        """更新 Google 商品覆盖字段（mpn/brand/custom_label 等）。"""
        with session_scope() as s:
            stmt = select(GoogleProductField).where(
                GoogleProductField.store_id == store_id,
                GoogleProductField.shopify_product_id == shopify_product_id,
            )
            if shopify_variant_id is None:
                stmt = stmt.where(GoogleProductField.shopify_variant_id.is_(None))
            else:
                stmt = stmt.where(GoogleProductField.shopify_variant_id == shopify_variant_id)
            row = s.execute(stmt).scalar_one_or_none()
            if row is None:
                row = GoogleProductField(
                    store_id=store_id,
                    shopify_product_id=shopify_product_id,
                    shopify_variant_id=shopify_variant_id,
                )
                s.add(row)
            for k in ("mpn", "brand", "gtin", "google_product_category", "condition",
                      "custom_label0", "custom_label1", "custom_label2", "custom_label3", "custom_label4"):
                if k in kwargs and kwargs[k] is not None:
                    setattr(row, k, str(kwargs[k]))
            s.flush()
            return self._gpf_dict(row)

    # ------------------------------------------------------------------
    # GMC Feed 生成
    # ------------------------------------------------------------------
    def generate_gmc_feed(
        self,
        store_id: int,
        country: str = "US",
        currency: str = "USD",
        availability_default: str = "in_stock",
    ) -> dict:
        """生成 GMC TSV feed（产品+变体+Google字段合并）。"""
        _FEED_DIR.mkdir(parents=True, exist_ok=True)
        rows: list[list[str]] = [_GMC_COLUMNS]

        with session_scope() as s:
            store = s.get(Store, store_id)
            domain = (store.primary_domain or store.domain or "").rstrip("/")
            prods = s.execute(
                select(Product).where(Product.store_id == store_id, Product.status == "active")
            ).scalars().all()
            gpf_map: dict[int, GoogleProductField] = {
                g.shopify_product_id: g
                for g in s.execute(
                    select(GoogleProductField).where(GoogleProductField.store_id == store_id)
                ).scalars()
            }
            variants = s.execute(
                select(ProductVariant).where(ProductVariant.store_id == store_id)
            ).scalars().all()
            variants_by_product: dict[int, list[ProductVariant]] = {}
            for v in variants:
                variants_by_product.setdefault(v.shopify_product_id, []).append(v)

            n = 0
            for p in prods:
                gpf = gpf_map.get(p.shopify_product_id)
                for v in variants_by_product.get(p.shopify_product_id, []):
                    link = f"https://{domain}/products/{p.handle}" if domain else p.handle
                    image = ""
                    if p.raw and isinstance(p.raw, dict):
                        imgs = p.raw.get("images") or []
                        if imgs:
                            image = imgs[0].get("src", "")
                    rows.append([
                        f"shopify_{country.upper()}_{p.shopify_product_id}_{v.shopify_variant_id}",
                        (p.title + (" - " + v.title if v.title and v.title != "Default Title" else ""))[:150],
                        (p.raw or {}).get("body_html", "") if isinstance(p.raw, dict) else "",
                        link,
                        image,
                        availability_default,
                        f"{v.price if v.price is not None else ''} {currency}",
                        gpf.brand if gpf and gpf.brand else p.vendor,
                        gpf.mpn if gpf and gpf.mpn else v.sku,
                        gpf.condition if gpf and gpf.condition else "new",
                        gpf.google_product_category if gpf else "",
                        gpf.custom_label0 if gpf else "",
                        gpf.custom_label1 if gpf else "",
                        gpf.custom_label2 if gpf else "",
                        gpf.custom_label3 if gpf else "",
                        gpf.custom_label4 if gpf else "",
                    ])
                    n += 1

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            feed_path = _FEED_DIR / f"gmc_feed_store{store_id}_{ts}.tsv"
            with open(feed_path, "w", encoding="utf-8", newline="") as f:
                for row in rows:
                    f.write("\t".join(_clean(c) for c in row) + "\n")

            feed = GmcFeed(
                store_id=store_id, feed_file=str(feed_path), product_count=n,
                status="generated", settings={"country": country, "currency": currency},
                generated_at=datetime.now(),
            )
            s.add(feed)
            logger.info(f"[marketing] GMC feed 生成 store={store_id} products={n} -> {feed_path}")
            return {"feed_file": str(feed_path), "product_count": n}

    def list_gmc_feeds(self, store_id: int, limit: int = 20) -> list[dict]:
        with session_scope() as s:
            rows = (
                s.execute(
                    select(GmcFeed)
                    .where(GmcFeed.store_id == store_id)
                    .order_by(GmcFeed.generated_at.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [
                {
                    "id": r.id, "feed_file": r.feed_file, "product_count": r.product_count,
                    "status": r.status, "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                }
                for r in rows
            ]

    # ------------------------------------------------------------------
    @staticmethod
    def _gpf_dict(r: GoogleProductField) -> dict:
        return {
            "id": r.id,
            "shopify_product_id": r.shopify_product_id,
            "shopify_variant_id": r.shopify_variant_id,
            "mpn": r.mpn, "brand": r.brand, "gtin": r.gtin,
            "google_product_category": r.google_product_category,
            "custom_labels": [r.custom_label0, r.custom_label1, r.custom_label2, r.custom_label3, r.custom_label4],
        }


def _clean(cell) -> str:
    """TSV 单元格清洗：去 HTML 标签/换行/制表符。"""
    import re

    text = str(cell or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\t", " ").replace("\n", " ").replace("\r", " ")
    return text.strip()
