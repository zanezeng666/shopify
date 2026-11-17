# -*- coding: utf-8 -*-
"""PMax 24441391608 定向修复：
1) add LOCATION US(2840)  2) add LANGUAGE English(1000)
3) targeting_setting GEO_TARGET → LOCATION_OF_PRESENCE(仅物理在美)
"""
import os

from google.protobuf import field_mask_pb2
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")
CAMP = "24441391608"

from google.ads.googleads.client import GoogleAdsClient

ads = GoogleAdsClient.load_from_dict({
    "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "unused"),
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", CID),
    "use_proto_plus": True,
})
ccs = ads.get_service("CampaignCriterionService")
cs = ads.get_service("CampaignService")

cres = ads.get_type("CampaignCriterion")
cres.campaign = f"customers/{CID}/campaigns/{CAMP}"
cres.location.geo_target_constant = "geoTargetConstants/2840"
op1 = ads.get_type("CampaignCriterionOperation")
op1.create = cres

cles = ads.get_type("CampaignCriterion")
cles.campaign = f"customers/{CID}/campaigns/{CAMP}"
cles.language.language_constant = "languageConstants/1000"
op2 = ads.get_type("CampaignCriterionOperation")
op2.create = cles

try:
    r = ccs.mutate_campaign_criteria(
        customer_id=CID, operations=[op1, op2])
    for res in r.results:
        print(f"  criterion OK: {res.resource_name}")
except Exception as e:
    print(f"  criteria: {str(e)[:150]} (已加过则忽略)")

# 3) presence 模式
camp_op = ads.get_type("CampaignOperation")
c = camp_op.update
c.resource_name = f"customers/{CID}/campaigns/{CAMP}"
tr = ads.get_type("TargetRestriction")
tr.targeting_dimension = ads.get_type("TargetingDimensionEnum").TargetingDimension.LOCATION
tr.restriction = ads.get_type("TargetingRestrictionEnum").TargetingRestriction.LOCATION_OF_PRESENCE
c.targeting_setting.target_restrictions.append(tr)
camp_op.update_mask.CopyFrom(
    field_mask_pb2.FieldMask(paths=["targeting_setting.target_restrictions"]))
r2 = cs.mutate_campaigns(customer_id=CID, operations=[camp_op])
print(f"  targeting_setting OK: {r2.results[0].resource_name}")
print("\nPMax 现定向: 美国(仅实际在美) + 英语")
