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
c = ads.get_type("Campaign")
pb = getattr(c, "_pb", c)
fd = pb.DESCRIPTOR.fields_by_name["targeting_setting"].message_type
sub = fd.fields_by_name["target_restrictions"].message_type
for f in sub.fields:
    if f.enum_type:
        print(f.name, "→", [v.name for v in f.enum_type.values])
