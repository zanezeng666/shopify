# -*- coding: utf-8 -*-
from shopify_admin.services.marketing.google_ads import (
    GoogleAdsConfigError,
    GoogleAdsCreds,
    GoogleAdsService,
)
from shopify_admin.services.marketing.service import MarketingService

__all__ = [
    "MarketingService",
    "GoogleAdsService",
    "GoogleAdsCreds",
    "GoogleAdsConfigError",
]
