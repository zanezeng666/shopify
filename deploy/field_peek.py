# -*- coding: utf-8 -*-
"""反射 proto-plus 类字段名"""
from google.ads.googleads.v26.resources.types import (
    campaign as camp,
    ad_group_criterion as agc,
    campaign_budget as cb,
)

for t, cls in (("Campaign", camp.Campaign),
               ("AdGroupCriterion", agc.AdGroupCriterion),
               ("CampaignBudget", cb.CampaignBudget)):
    print(f"=== {t} ===")
    for name in cls._meta.fields:
        if any(k in name for k in ("bidding", "maximize", "serving", "clicks")):
            print(f"  {name}")
