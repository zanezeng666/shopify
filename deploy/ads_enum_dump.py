# -*- coding: utf-8 -*-
from google.ads.googleads.v26.enums.types.\
    listing_group_filter_product_type_level import (
    ListingGroupFilterProductTypeLevelEnum,
)
E = ListingGroupFilterProductTypeLevelEnum.ListingGroupFilterProductTypeLevel
print([(n, getattr(E, n)) for n in dir(E) if not n.startswith("_")])
