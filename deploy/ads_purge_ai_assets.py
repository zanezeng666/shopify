# -*- coding: utf-8 -*-
"""PMax 医疗系列：
1) 验证「文案适配」(text asset automation) 开关状态
2) 删除 Google AI 生成素材（asset_group_asset.added_by_google_ads=True 的
   文本类），我们配置的素材(added_by=False)绝不触碰
3) 复核清零
"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608
AG = 6770847164

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")


def rows(q, label=""):
    try:
        return list(gas.search(customer_id=CID, query=q))
    except Exception as e:  # noqa: BLE001
        errs = getattr(e, "errors", [])
        msg = errs[0].message[:220] if errs else str(e)[:500]
        print(f"  [查询失败:{label}] {msg}")
        return []


print("=== 1. 文案适配开关状态（asset_automation_setting） ===")
aar = rows(
    "SELECT asset_automation_setting.asset_automation_type, "
    "asset_automation_setting.field_type, "
    "asset_automation_setting.status "
    "FROM asset_automation_setting "
    f"WHERE campaign.id = {PMAX}", "aas")
if not aar:
    print("  （API 不可读该设置——以后台为准）")
for r in aar:
    s = r.asset_automation_setting
    print(f"  {s.asset_automation_type.name} / {s.field_type.name}"
          f" → status={s.status.name}")

print("\n=== 2. 资产组内 Google AI 生成素材清单 ===")
q = ("SELECT asset_group_asset.resource_name, asset_group_asset.status, "
     "asset_group_asset.field_type, "
     "asset_group_asset.added_by_google_ads, asset.name, "
     "asset.text_asset.text "
     "FROM asset_group_asset "
     f"WHERE asset_group.id = {AG}")
all_rows = rows(q, "aga")
if not all_rows:
    raise SystemExit("资产组查询失败，中止（未做任何改动）")

mine_cnt = ai_rows = 0
to_remove = []
for r in all_rows:
    a = r.asset_group_asset
    ft = a.field_type.name
    if a.added_by_google_ads and a.status.name == "ENABLED":
        ai_rows += 1
        if ft in ("HEADLINE", "LONG_HEADLINE", "DESCRIPTION"):
            to_remove.append(a.resource_name)
            txt = (r.asset.text_asset.text or "")[:56]
            print(f"  [AI·删] {ft:12} {txt}")
        else:
            print(f"  [AI·非文本跳过] {ft}")
    elif a.added_by_google_ads:
        print(f"  [AI·非ENABLED({a.status.name})跳过] {ft}")
    else:
        mine_cnt += 1
print(f"\n合计: 我们配置保留 {mine_cnt} | Google AI 文本待删 "
      f"{len(to_remove)}")
if not to_remove:
    print("没有 Google AI 生成的文本素材，无需删除。")
    raise SystemExit(0)

print(f"\n=== 3. 执行移除 {len(to_remove)} 个 ===")
agas = client.get_service("AssetGroupAssetService")
ok = fail = 0
for i in range(0, len(to_remove), 20):
    batch = to_remove[i:i + 20]
    ops = []
    for rn in batch:
        op = client.get_type("AssetGroupAssetOperation")
        op.remove = rn
        ops.append(op)
    try:
        resp = agas.mutate_asset_group_assets(
            customer_id=CID, operations=ops)
        ok += len(resp.results)
    except Exception as e:  # noqa: BLE001
        errs = getattr(e, "errors", [])
        msg = errs[0].message[:200] if errs else str(e)[:200]
        fail += len(batch)
        print(f"  ✗ 批次失败: {msg}")
print(f"移除完成: ok={ok} fail={fail}")

print("\n=== 4. 复核 ===")
left = rows(
    "SELECT asset_group_asset.resource_name, asset_group_asset.status, "
    "asset_group_asset.added_by_google_ads, "
    "asset_group_asset.field_type "
    "FROM asset_group_asset "
    f"WHERE asset_group.id = {AG}", "aga2")
ai_left = sum(1 for r in left
              if r.asset_group_asset.added_by_google_ads
              and r.asset_group_asset.status.name == "ENABLED")
mine_left = sum(1 for r in left
                if not r.asset_group_asset.added_by_google_ads)
print(f"资产组剩余: 我们配置 {mine_left} | Google AI 残留 {ai_left}")
print("✓ 清理干净" if ai_left == 0 else "⚠ 仍有 AI 残留（见上）")
