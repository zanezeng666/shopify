# -*- coding: utf-8 -*-
"""查定价 job 状态 + 上次重算结果 + 手动触发一次全量重算。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.config.settings import settings  # noqa: E402

print("recalc_cron:", settings.scheduler_price_recalc_cron)
print("scheduler_enabled:", getattr(settings, "scheduler_enabled", "?"))

from shopify_admin.services.pricing import PricingService  # noqa: E402
svc = PricingService()
d = svc.recalc_store_prices(store_id=1)
print("recalc:", d)
