# -*- coding: utf-8 -*-
"""给 Search 补 CPC 出价上限 ¥11（≈$1.5，原设计的保险丝，当时未生效）。"""
import os

from dotenv import load_dotenv
from google.protobuf import field_mask_pb2
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
SEARCH = f"customers/{CID}/campaigns/24448362668"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})

# 探测 v26 Campaign 实际字段名（maximize_clicks 或 target_spend）
camp = client.get_type("Campaign")
fields = [n for n in camp._pb.DESCRIPTOR.fields_by_name
          if "click" in n or "spend" in n]
print("候选字段:", fields)
field_name = "maximize_clicks" if "maximize_clicks" in fields else "target_spend"

cs = client.get_service("CampaignService")
op = client.get_type("CampaignOperation")
op.update.resource_name = SEARCH
getattr(op.update, field_name).cpc_bid_ceiling_micros = 11_000_000
op.update_mask.CopyFrom(field_mask_pb2.FieldMask(
    paths=[f"{field_name}.cpc_bid_ceiling_micros"]))
cs.mutate_campaigns(customer_id=CID, operations=[op])
print(f"cpc上限已设 ¥11（via {field_name}）")

gas = client.get_service("GoogleAdsService")
rows = list(gas.search(customer_id=CID, query=(
    "SELECT campaign.target_spend.cpc_bid_ceiling_micros "
    f"FROM campaign WHERE campaign.resource_name='{SEARCH}'")))
print("readback:",
      rows[0].campaign.target_spend.cpc_bid_ceiling_micros / 1e6, "CNY")
