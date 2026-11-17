# -*- coding: utf-8 -*-
"""查 SMTP 是否已配置 + shop.email。"""
import sys

sys.path.insert(0, "/data/bmai/src")
from sqlalchemy import text  # noqa: E402
from bmai.core.database import cs_engine  # noqa: E402
from bmai.config.settings import settings  # noqa: E402

eng = cs_engine.engine
with eng.connect() as c:
    rows = c.execute(text(
        "SELECT cfg_key, LEFT(cfg_value, 20) FROM bmai_config "
        "WHERE cfg_key LIKE 'smtp%'")).fetchall()
    print("smtp cfg:", rows or "NONE")
print("settings.smtp_host:", repr(settings.smtp_host[:8]) if settings.smtp_host else "(empty)")

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
client = StoreService().get_client(1)
r = client.graphql("{shop{email staffAccounts(first:1){edges{node{email}}}}}")
print("shop:", str(r)[:220])
