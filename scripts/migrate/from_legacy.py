# -*- coding: utf-8 -*-
"""老库 shopify -> 新库 shopify_new 迁移（只读老库，分批幂等可重跑）。

用法：
    uv run python scripts/migrate/from_legacy.py --dry-run          # 只统计不写
    uv run python scripts/migrate/from_legacy.py                    # 全量迁移
    uv run python scripts/migrate/from_legacy.py --only stores,orders

映射：
    shopify_store_info  -> stores            （username/api_key 双唯一键 upsert）
    orders_report       -> orders + order_items（行项级聚合；order_item_id "shopify#N" 解析行项序号）
    shopify_product     -> products
    product_variant     -> product_variants

老 status -> 新 local_status:
    shipped->completed  cancel->cancelled  error->failed
    process->submitted  new/waiting_for_stock->pending

跳过（新系统不消费）：gmc_feed（Google 绩效数据）、buy_on_google、google_metafields（0 行）。
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from loguru import logger
from sqlalchemy import text

from shopify_admin.core.database import get_legacy_engine, session_scope
from shopify_admin.models.order import Order, OrderItem
from shopify_admin.models.product import Product, ProductVariant
from shopify_admin.models.store import Store

BATCH = 500

_STATUS_MAP = {
    "shipped": "completed",
    "cancel": "cancelled",
    "error": "failed",
    "process": "submitted",
    "new": "pending",
    "waiting_for_stock": "pending",
}

_SHOPIFY_ITEM_RE = re.compile(r"shopify#(\d+)")


def _to_bool(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes")


def _to_int(v) -> int | None:
    """老库 Shopify ID 多为 VARCHAR，统一转 int（与新库 BIGINT 键对齐）。"""
    if v is None:
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _to_dt(v) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    s = str(v).strip()
    if not s:
        return None
    try:  # ISO 带时区，截断为 naive
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s[:19] if " " in s else s[:10], fmt)
            except ValueError:
                continue
    return None


def _to_dec(v) -> Decimal | None:
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        return None


# ----------------------------------------------------------------------
def migrate_stores(dry_run: bool) -> int:
    with get_legacy_engine().connect() as c:
        rows = c.execute(text(
            "SELECT api_key, api_secret, domain, is_available, username, Rcustomerno, "
            "is_inventory_available, main_ship_by, ship_of_country_first FROM shopify_store_info"
        )).fetchall()
    logger.info(f"[stores] 老库 {len(rows)} 行")
    if dry_run:
        return len(rows)
    n = 0
    with session_scope() as s:
        for r in rows:
            (api_key, api_secret, domain, is_avail, username,
             rcustomerno, inv_avail, main_ship_by, ship_first) = r
            store = s.execute(
                text("SELECT * FROM stores WHERE username = :u"), {"u": username}
            ).first()
            if store is None:
                store = s.execute(
                    text("SELECT * FROM stores WHERE api_key = :k"), {"k": api_key}
                ).first()
            if store is None:
                st = Store(
                    username=username, api_key=api_key, api_secret=api_secret or "",
                    domain=domain or "", is_available=_to_bool(is_avail),
                    is_inventory_available=_to_bool(inv_avail),
                    rcustomerno=int(rcustomerno) if rcustomerno else None,
                    main_ship_by=main_ship_by or "",
                    ship_of_country_first=str(ship_first or ""),
                )
                s.add(st)
                n += 1
                logger.info(f"[stores] 新增 {username} ({domain})")
            else:
                logger.info(f"[stores] 已存在跳过 {username}")
    return n


# ----------------------------------------------------------------------
def _flush_orders(pending: list) -> None:
    """订单先 flush 拿自增 id，行项以 order_id 关联落库。"""
    with session_scope() as s:
        for o, its in pending:
            s.add(o)
            s.flush()
            for it in its:
                it.order_id = o.id
                s.add(it)


def migrate_orders(dry_run: bool) -> int:
    """orders_report 行项级 -> orders + order_items（按订单号聚合）。"""
    # store_name -> store_id 映射（老库 store_name 实为店铺 domain，username/domain 都入键）
    stores: dict[str, int] = {}
    with session_scope() as s:
        for sid, username, domain in s.execute(text("SELECT id, username, domain FROM stores")):
            if username:
                stores[str(username).strip().lower()] = sid
            if domain:
                stores[str(domain).strip().lower()] = sid

    eng = get_legacy_engine()
    with eng.connect() as c:
        total = c.execute(text("SELECT COUNT(*) FROM orders_report")).scalar()
        logger.info(f"[orders] 老库 {total} 行（行项级）")
        rows = c.execute(text(
            "SELECT order_id, order_item_id, status, store_name, order_date, order_details, "
            "order_tracking_no, address, zip_code, city, country, province, full_address, "
            "recipient_name, phone_number, sku, quantity, cs_id, ship_by, warehouse_name, "
            "cs_total_amount, purchase_date, email FROM orders_report ORDER BY order_id"
        )).fetchall()
    if dry_run:
        return len(rows)

    # 已迁移的订单（幂等）：跳过已存在的 shopify_order_id
    with session_scope() as s:
        done = {r[0] for r in s.execute(text("SELECT shopify_order_id FROM orders"))}

    by_order: dict[str, list] = {}
    for r in rows:
        by_order.setdefault(str(r[0]), []).append(r)

    n_orders = n_items = skipped = 0
    pending: list = []
    for order_id, items in by_order.items():
        if int(order_id) in done:
            skipped += 1
            continue
        first = items[0]
        store_id = stores.get(str(first[3] or "").strip().lower())
        if store_id is None:
            logger.warning(f"[orders] 店铺未迁移? store_name={first[3]}，跳过订单 {order_id}")
            continue
        # 老列顺序：7=address, 8=zip_code, 9=city, 10=country, 11=province, 12=full_address
        addr = {
            "name": first[13] or "", "phone": first[14] or "",
            "address1": first[7] or "", "city": first[9] or "",
            "province": first[11] or "", "zip": first[8] or "",
            "country_code": first[10] or "", "address2": "",
        }
        tracking = first[6] or ""
        local_status = _STATUS_MAP.get(first[2], "pending")
        order = Order(
            store_id=store_id,
            shopify_order_id=int(order_id),
            name=f"#{order_id[-4:]}" if order_id.isdigit() else order_id,
            email=first[22] or "",
            phone=first[14] or "",
            financial_status="paid" if local_status not in ("cancelled",) else "voided",
            fulfillment_status="fulfilled" if local_status == "completed" else "unfulfilled",
            local_status=local_status,
            channel="cs" if (first[18] or "").startswith("CS") else "",
            shipping_address=addr,
            processed_at=_to_dt(first[21]),
            shopify_created_at=_to_dt(first[4]),
            raw={"legacy": True, "tracking_no": tracking,
                 "ship_by": first[18] or "", "warehouse": first[19] or "",
                 "full_address": first[12] or "", "order_details": first[5] or ""},
        )
        s_items = []
        for it in items:
            m = _SHOPIFY_ITEM_RE.match(str(it[1] or ""))
            try:
                qty = int(it[16] or 1)
            except (TypeError, ValueError):
                qty = 1
            s_items.append(OrderItem(
                shopify_line_item_id=int(m.group(1)) if m else abs(hash(f"{it[0]}:{it[1]}")) % (10 ** 12),
                sku=it[15] or "", cs_id=it[17] or "",
                quantity=qty,
            ))
        pending.append((order, s_items))
        n_orders += 1
        n_items += len(s_items)
        if len(pending) >= BATCH:
            _flush_orders(pending)
            logger.info(f"[orders] 已迁移 {n_orders} 单 / {n_items} 行项（跳过 {skipped}）")
            pending = []
    if pending:
        _flush_orders(pending)
    logger.info(f"[orders] 完成：{n_orders} 单 / {n_items} 行项，幂等跳过 {skipped}")
    return n_orders


# ----------------------------------------------------------------------
def migrate_products(dry_run: bool) -> int:
    eng = get_legacy_engine()
    with eng.connect() as c:
        total = c.execute(text("SELECT COUNT(*) FROM shopify_product")).scalar()
        logger.info(f"[products] 老库 {total} 行")
    if dry_run:
        return total
    # 老库产品表无店铺归属（老系统单店铺事实）——挂到第一个店铺
    with session_scope() as s:
        row = s.execute(text("SELECT id, username FROM stores ORDER BY id LIMIT 1")).first()
        if row is None:
            logger.error("[products] 无店铺，先迁移 stores")
            return 0
        store_id, store_name = row
        done = {_to_int(r[0]) for r in s.execute(text("SELECT shopify_product_id FROM products"))}
    logger.info(f"[products] 归属店铺 {store_name}(#{store_id})")
    n = 0
    last_id = 0
    while True:
        with eng.connect() as c:
            rows = c.execute(text(
                "SELECT id, title, body_html, vendor, product_type, created_at, handle, "
                "updated_at, status, tags, admin_graphql_api_id, seo FROM shopify_product "
                "WHERE CAST(id AS UNSIGNED) > :lid ORDER BY CAST(id AS UNSIGNED) LIMIT :lim"
            ), {"lid": last_id, "lim": BATCH}).fetchall()
        if not rows:
            break
        with session_scope() as s:
            for r in rows:
                last_id = max(last_id, _to_int(r[0]) or 0)
                if _to_int(r[0]) in done:
                    continue
                seo = {}
                if r[11]:
                    try:
                        import json

                        seo = json.loads(r[11]) if str(r[11]).strip().startswith(("{", "[")) else {}
                    except Exception:  # noqa: BLE001
                        seo = {}
                s.add(Product(
                    store_id=store_id,
                    shopify_product_id=_to_int(r[0]), title=r[1] or "", handle=r[6] or "",
                    vendor=r[3] or "", product_type=r[4] or "",
                    status=r[8] or "active", tags=r[9] or "",
                    seo_title=str(seo.get("title", ""))[:512],
                    seo_description=str(seo.get("description", "")),
                    shopify_created_at=_to_dt(r[5]), shopify_updated_at=_to_dt(r[7]),
                    raw={"legacy": True, "body_html": r[2] or "",
                         "admin_graphql_api_id": r[10] or ""},
                ))
                n += 1
        logger.info(f"[products] 进度 id>{last_id} 新增 {n}")
    logger.info(f"[products] 完成：新增 {n}，幂等跳过 {total - n}")
    return n


def migrate_variants(dry_run: bool) -> int:
    eng = get_legacy_engine()
    with eng.connect() as c:
        total = c.execute(text("SELECT COUNT(*) FROM product_variant")).scalar()
        logger.info(f"[variants] 老库 {total} 行")
    if dry_run:
        return total
    with session_scope() as s:
        store_id = s.execute(text("SELECT MIN(id) FROM stores")).scalar()
        prod_map = {_to_int(r[0]): r[1] for r in s.execute(text("SELECT shopify_product_id, id FROM products"))}
        done = {_to_int(r[0]) for r in s.execute(text("SELECT shopify_variant_id FROM product_variants"))}
    n = 0
    last_id = 0
    while True:
        with eng.connect() as c:
            rows = c.execute(text(
                "SELECT id, product_id, title, price, sku, position, compare_at_price, "
                "created_at, updated_at, barcode, grams, inventory_item_id, "
                "inventory_quantity, cs_id, option1, option2, option3 FROM product_variant "
                "WHERE CAST(id AS UNSIGNED) > :lid ORDER BY CAST(id AS UNSIGNED) LIMIT :lim"
            ), {"lid": last_id, "lim": BATCH}).fetchall()
        if not rows:
            break
        with session_scope() as s:
            for r in rows:
                last_id = max(last_id, _to_int(r[0]) or 0)
                if _to_int(r[0]) in done:
                    continue
                local_pid = prod_map.get(_to_int(r[1]))
                if local_pid is None:
                    continue  # 产品未迁移（孤儿变体）
                s.add(ProductVariant(
                    store_id=store_id, product_id=local_pid,
                    shopify_variant_id=_to_int(r[0]), shopify_product_id=_to_int(r[1]),
                    inventory_item_id=_to_int(r[11]),
                    title=r[2] or "", price=_to_dec(r[3]), sku=r[4] or "",
                    compare_at_price=_to_dec(r[6]),
                    barcode=r[9] or "", grams=int(r[10] or 0),
                    option1=r[14] or "", option2=r[15] or "", option3=r[16] or "",
                    shopify_updated_at=_to_dt(r[8]),
                    raw={"legacy": True, "position": r[5] or 0,
                         "inventory_quantity": int(r[12] or 0),
                         "cs_id": r[13] or ""},
                ))
                n += 1
        logger.info(f"[variants] 进度 id>{last_id} 新增 {n}")
    logger.info(f"[variants] 完成：新增 {n}")
    return n


# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="老库 -> shopify_new 迁移")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写库")
    parser.add_argument("--only", default="", help="逗号分隔：stores,orders,products,variants")
    args = parser.parse_args()

    only = {x.strip() for x in args.only.split(",") if x.strip()} or {"stores", "orders", "products", "variants"}
    logger.info(f"迁移开始 dry_run={args.dry_run} scope={sorted(only)}")

    if "stores" in only:
        migrate_stores(args.dry_run)
    if "orders" in only:
        migrate_orders(args.dry_run)
    if "products" in only:
        migrate_products(args.dry_run)
    if "variants" in only:
        migrate_variants(args.dry_run)
    logger.info("迁移结束")


if __name__ == "__main__":
    main()
