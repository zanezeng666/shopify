# -*- coding: utf-8 -*-
"""纯反射：AssetGroupSignal.audience (AudienceInfo) 的字段结构"""
import os

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")

from google.ads.googleads.client import GoogleAdsClient

ads = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "login_customer_id": CID,
    "use_proto_plus": True,
})


def dump(msg, name, depth=0):
    pb = getattr(msg, "_pb", msg)
    for f in pb.DESCRIPTOR.fields:
        ind = "  " * (depth + 1)
        if f.enum_type:
            vals = [v.name for v in f.enum_type.values]
            print(f"{ind}{f.name} enum: {vals[:10]}")
        elif f.message_type:
            print(f"{ind}{f.name}: msg[{f.label}]")
            if depth < 3:
                dump(getattr(msg, f.name, None) or type(msg).FromString(b"") if False else msg.__class__.__dict__.get(f.name, None), f.name, depth + 1) if False else _dump_desc(f.message_type, depth + 1)
        else:
            print(f"{ind}{f.name}: {f.type}")


def _dump_desc(desc, depth):
    for f in desc.fields:
        ind = "  " * (depth + 1)
        if f.enum_type:
            print(f"{ind}{f.name} enum: {[v.name for v in f.enum_type.values][:10]}")
        elif f.message_type:
            print(f"{ind}{f.name}: msg[{f.label}]")
            if depth < 3:
                _dump_desc(f.message_type, depth + 1)
        else:
            print(f"{ind}{f.name}: scalar")


sig = ads.get_type("AssetGroupSignal")
aipb = getattr(sig.audience, "_pb", sig.audience)
print("AudienceInfo:")
_dump_desc(aipb.DESCRIPTOR, 0)
