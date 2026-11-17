# -*- coding: utf-8 -*-
"""品牌词 asset 根除：定位挂载 → AssetService REMOVE → 复核。
安全边界：只删文本含品牌词的 45 个 asset；RSA 9 标题/33 素材全医疗词不会命中。
"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")


def rows(q):
    return list(gas.search(customer_id=CID, query=q))


BRAND = ("jbl", "bose", "soundlink", "craftsman", "nextec",
         "styles:", "flip 4", "flip4", "dremel", "ryobi", "dewalt",
         "makita", "milwaukee", "cameron", "cameron sino")

print("=== 1. 定位品牌词 asset ===")
assets = [(r.asset.resource_name, (r.asset.text_asset.text or "").strip())
          for r in rows("SELECT asset.resource_name, asset.text_asset.text "
                        "FROM asset")]
targets = {rn: t for rn, t in assets
           if t and any(w in t.lower() for w in BRAND)}
print(f"  命中 {len(targets)} 个")
tset = set(targets)

print("\n=== 2. 挂载关系 ===")
# 2a. asset_group_asset（全账号所有资产组）
linked = {}
for r in rows("SELECT asset_group_asset.resource_name, "
              "asset_group_asset.asset, asset_group_asset.status, "
              "asset_group.id, asset_group.name "
              "FROM asset_group_asset"):
    if r.asset_group_asset.asset in tset:
        linked[r.asset_group_asset.asset] = (
            r.asset_group.name[:40],
            r.asset_group_asset.status.name,
            r.asset_group_asset.resource_name)
# 2b. campaign_asset
camp_linked = {}
for r in rows("SELECT campaign_asset.resource_name, "
              "campaign_asset.asset, campaign_asset.status, "
              "campaign_asset.campaign "
              "FROM campaign_asset"):
    if r.campaign_asset.asset in tset:
        camp_linked[r.campaign_asset.asset] = (
            r.campaign_asset.campaign, r.campaign_asset.status.name)
print(f"  挂在资产组: {len(linked)}")
for a, (g, st, _) in list(linked.items())[:8]:
    print(f"    组[{g}] {st}: {targets[a][:44]}")
print(f"  挂在系列级: {len(camp_linked)}")
for a, (c, st) in list(camp_linked.items())[:8]:
    print(f"    系列[{c.rsplit('/', 1)[-1]}] {st}: {targets[a][:44]}")
unlinked = [a for a in tset if a not in linked and a not in camp_linked]
print(f"  无任何关联（游离）: {len(unlinked)}")

print(f"\n=== 3. AssetService REMOVE {len(targets)} 个 ===")
asvc = client.get_service("AssetService")
ok = fail = 0
errs = []
for i in range(0, len(targets), 25):
    batch = list(targets)[i:i + 25]
    ops = []
    for rn in batch:
        op = client.get_type("AssetOperation")
        op.remove = rn
        ops.append(op)
    try:
        resp = asvc.mutate_assets(customer_id=CID, operations=ops)
        ok += len(resp.results)
    except Exception as e:  # noqa: BLE001
        errs.append(str(e)[:300])
        fail += len(batch)
if errs:
    print(f"  失败详情(前2): {errs[:2]}")
print(f"  删除结果: ok={ok} fail={fail}")

print("\n=== 4. 复核 ===")
left = [(r.asset.resource_name, (r.asset.text_asset.text or "").strip())
        for r in rows("SELECT asset.resource_name, asset.text_asset.text "
                      "FROM asset")]
remain = [t for _, t in left
          if t and any(w in t.lower() for w in BRAND)]
print(f"  asset 池剩余品牌词命中: {len(remain)}")
print("  " + ("✓ 已根除" if not remain else
              f"⚠ 残留: {remain[:5]}"))
