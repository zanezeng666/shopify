# -*- coding: utf-8 -*-
"""探 v26 Asset 全字段找视频上传路径。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
fields = client.get_type("Asset")._pb.DESCRIPTOR.fields_by_name
print("v26 Asset 字段:")
for k in sorted(fields):
    t = fields[k].message_type.full_name if fields[k].message_type else fields[k].type
    mark = " <<<" if "video" in k.lower() else ""
    print(f"  {k}: {t}{mark}")
