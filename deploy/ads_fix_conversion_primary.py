# -*- coding: utf-8 -*-
"""修复 PMax 转化目标受限：GA4 purchase #947144115 升为 primary。"""
import os

from dotenv import load_dotenv
from google.protobuf import field_mask_pb2
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
CA = f"customers/{CID}/conversionActions/947144115"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
cas = client.get_service("ConversionActionService")
op = client.get_type("ConversionActionOperation")
op.update.resource_name = CA
op.update.primary_for_goal = True
op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["primary_for_goal"]))
res = cas.mutate_conversion_actions(
    customer_id=CID, operations=[op])
print("修改结果:", res.results[0].resource_name)

gas = client.get_service("GoogleAdsService")
rows = list(gas.search(customer_id=CID, query=(
    "SELECT conversion_action.name, conversion_action.status, "
    "conversion_action.category, conversion_action.primary_for_goal "
    f"FROM conversion_action WHERE conversion_action.resource_name = '{CA}'")))
ca = rows[0].conversion_action
print(f"readback: {ca.name} | {ca.status.name} | {ca.category.name} "
      f"| primary={ca.primary_for_goal}")
