"""拉取各市场 regions 名单（name=国家名），映射 ISO2 对照 31 失败国。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)

NAME2ISO = {
    "united states": "US", "canada": "CA", "mexico": "MX",
    "united kingdom": "GB", "england": "GB", "ireland": "IE",
    "france": "FR", "germany": "DE", "austria": "AT", "belgium": "BE",
    "netherlands": "NL", "spain": "ES", "portugal": "PT", "italy": "IT",
    "greece": "GR", "denmark": "DK", "sweden": "SE", "norway": "NO",
    "finland": "FI", "iceland": "IS", "switzerland": "CH",
    "luxembourg": "LU", "malta": "MT", "cyprus": "CY",
    "poland": "PL", "czechia": "CZ", "czech republic": "CZ",
    "slovakia": "SK", "slovenia": "SI", "hungary": "HU", "romania": "RO",
    "bulgaria": "BG", "croatia": "HR", "estonia": "EE", "latvia": "LV",
    "lithuania": "LT", "ukraine": "UA", "moldova": "MD", "serbia": "RS",
    "japan": "JP", "south korea": "KR", "korea, republic of": "KR",
    "thailand": "TH", "singapore": "SG", "malaysia": "MY",
    "indonesia": "ID", "vietnam": "VN", "philippines": "PH",
    "cambodia": "KH", "kazakhstan": "KZ", "india": "IN",
    "australia": "AU", "new zealand": "NZ",
    "brazil": "BR", "chile": "CL", "colombia": "CO", "peru": "PE",
    "argentina": "AR",
    "saudi arabia": "SA", "united arab emirates": "AE", "bahrain": "BH",
    "qatar": "QA", "kuwait": "KW", "oman": "OM", "jordan": "JO",
    "turkey": "TR", "turkiye": "TR", "israel": "IL", "egypt": "EG",
    "south africa": "ZA",
    "hong kong sar": "HK", "hong kong": "HK", "macao": "MO",
    "taiwan": "TW",
}

q = """
{ markets(first: 20) { nodes { id handle name enabled type
  conditions { regionsCondition { applicationLevel
    regions(first: 250) { nodes { id name } } } } } } }
"""
mc = client.graphql(q)
all_codes = set()
unmapped = set()
for m in mc["markets"]["nodes"]:
    rc = m["conditions"]["regionsCondition"]
    names = [r["name"] for r in rc["regions"]["nodes"]]
    codes = set()
    for n in names:
        iso = NAME2ISO.get(n.strip().lower())
        if iso:
            codes.add(iso)
        else:
            unmapped.add(n)
    all_codes |= codes
    print(f'\n[{m["name"]}] type={m.get("type")} enabled={m["enabled"]} '
          f'appLevel={rc.get("applicationLevel")} regions={len(names)}')
    print("  names:", ", ".join(sorted(names))[:500])
    print("  iso:", ",".join(sorted(codes)))

if unmapped:
    print("\n未映射名:", ", ".join(sorted(unmapped)))
print(f"\n市场覆盖 ISO 国家总数(已映射): {len(all_codes)}")
bad = ("BR CH CL CO CY DK EE ES FI FR HU IE LT LU LV MD MT MY NL NO NZ "
       "PE PH PL PT RO RS SE SI SK UA").split()
missing = [c for c in bad if c not in all_codes]
covered = [c for c in bad if c in all_codes]
print(f"31 失败国已被市场覆盖: {covered}")
print(f"31 失败国不在任何市场: {len(missing)} -> {missing}")
