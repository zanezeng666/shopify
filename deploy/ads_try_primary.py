# -*- coding: utf-8 -*-
"""proto 客户端试改 primary_for_goal，拿具体错误详情。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.protobuf import field_mask_pb2

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
cas = client.get_service("ConversionActionService")
op = client.get_type("ConversionActionOperation")
op.update.resource_name = f"customers/{CID}/conversionActions/441327991"
op.update.primary_for_goal = False
op.update_mask.CopyFrom(
    field_mask_pb2.FieldMask(paths=["primary_for_goal"]))
try:
    resp = cas.mutate_conversion_actions(
        customer_id=CID, operations=[op])
    print("OK:", resp.results[0].resource_name)
except Exception as e:
    msg = str(e)
    print("FAIL:", msg[:600])
