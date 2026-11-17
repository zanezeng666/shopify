"""预算向 Search 倾斜：PMax $20→$10（保基础），Search $15→$25（倾斜），总量 $35 不变。
幂等：已是目标值则跳过。防御：若预算为多 campaign 共用则不改、报警。"""
import os

from dotenv import load_dotenv
from google.protobuf import field_mask_pb2
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

SHIFTS = {
    24441391608: ("PMax Medical Estry", 200),   # ¥200/天，用户 2026-11-12 指示
    24448362668: ("Estry Medical Search", 100),  # ¥100/天，用户 2026-11-12 指示
}


def main():
    client = GoogleAdsClient.load_from_dict({
        "developer_token": "unused",
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "use_proto_plus": True,
    })
    gas = client.get_service("GoogleAdsService")
    bs = client.get_service("CampaignBudgetService")

    for cid, (name, usd) in SHIFTS.items():
        rows = list(gas.search(customer_id=CID, query=(
            "SELECT campaign_budget.resource_name, campaign_budget.amount_micros "
            "FROM campaign WHERE campaign.id = %d" % cid)))
        if not rows:
            print(f"[{name}] campaign {cid} 不存在，跳过")
            continue
        rn = rows[0].campaign_budget.resource_name
        old = rows[0].campaign_budget.amount_micros / 1e6
        if abs(old - usd) < 0.01:
            print(f"[{name}] 已是 ${usd:.0f}/天，跳过")
            continue

        users = list(gas.search(customer_id=CID, query=(
            "SELECT campaign.id FROM campaign "
            f"WHERE campaign_budget.resource_name = '{rn}'")))
        if len(users) > 1:
            print(f"[{name}] 预算被 {len(users)} 个 campaign 共用，人工确认后再改，跳过")
            continue

        op = client.get_type("CampaignBudgetOperation")
        op.update.resource_name = rn
        op.update.amount_micros = int(usd * 1_000_000)
        op.update_mask.CopyFrom(
            field_mask_pb2.FieldMask(paths=["amount_micros"]))
        bs.mutate_campaign_budgets(customer_id=CID, operations=[op])
        print(f"[{name}] ¥{old:.0f} -> ¥{usd}/day ✓")

    # readback
    print("\n=== readback ===")
    for cid, (name, _) in SHIFTS.items():
        rows = list(gas.search(customer_id=CID, query=(
            "SELECT campaign.status, campaign_budget.amount_micros "
            "FROM campaign WHERE campaign.id = %d" % cid)))
        if rows:
            r = rows[0]
            print(f"{name}: {r.campaign_budget.amount_micros/1e6:.0f}/天 "
                  f"({r.campaign.status.name})")


if __name__ == "__main__":
    main()
