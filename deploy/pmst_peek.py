# -*- coding: utf-8 -*-
"""反射 campaign_search_term_view / customer_search_term_insight 字段"""
from google.ads.googleads.v26.resources.types import (
    campaign_search_term_view as c,
    customer_search_term_insight as u,
)

print("campaign_search_term_view:", [n for n in c.CampaignSearchTermView._meta.fields])
print("customer_search_term_insight:", [n for n in u.CustomerSearchTermInsight._meta.fields])
