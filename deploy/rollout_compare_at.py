"""全店批量划线价：compare_at = price×1.18 → .99 心理价（discount>25% 退精确值）。
用法: rollout_compare_at.py fetch|dryrun|apply1|apply
  fetch  : GraphQL 拉全店 active 产品+变体 → /tmp/ca_products.json
  dryrun : 公式计算 → deploy/rollout_dryrun.md + /tmp/ca_plan.json
  apply1 : 按 plan 只写第 1 个产品（schema 冒烟）
  apply  : 全量写（断点续跑 deploy/rollout_done.jsonl，适合 nohup 后台）
"""
import json
import sys
import time
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

CACHE = "/tmp/ca_products.json"
PLAN = "/tmp/ca_plan.json"
DONE = "/home/jason/shopify-admin/deploy/rollout_done.jsonl"
REPORT = "/home/jason/shopify-admin/deploy/rollout_dryrun.md"
gql = ShopifyRest(StoreService().get_client(1)).client.graphql

FETCH_Q = """
query($c: String, $qc: String) {
  products(first: 25, after: $c, query: $qc) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      variants(first: 25) {
        pageInfo { hasNextPage }
        nodes { id price compareAtPrice }
      }
    }
  }
}"""

MUT = """
mutation($pid: ID!, $vs: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $pid, variants: $vs) {
    productVariants { id compareAtPrice }
    userErrors { field message }
  }
}"""


def anchor_for(price_str: str):
    """返回 (compare_at 字符串 | None, 备注)。规则见文件头。"""
    p = Decimal(price_str)
    if p <= 0:
        return None, "price<=0"
    raw = p * Decimal("1.18")
    c99 = (raw - Decimal("0.99")).to_integral_value(rounding=ROUND_CEILING) + Decimal("0.99")
    disc = 1 - p / c99
    if disc > Decimal("0.25"):  # 低价 SKU ceil99 失真 → 用精确值（仍在 ~15%）
        c99 = raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        disc = 1 - p / c99
    if disc <= 0 or disc > Decimal("0.30"):
        return None, f"discount异常({disc:.0%})"
    return f"{c99:.2f}", f"{disc:.1%}"


def fetch():
    cursor, total_p, total_v, over25 = None, 0, 0, 0
    out = []
    while True:
        d = gql(FETCH_Q, {"c": cursor, "qc": "status:active"})
        prods = d["products"]
        for p in prods["nodes"]:
            total_p += 1
            vs = [(v["id"], v["price"], v.get("compareAtPrice")) for v in p["variants"]["nodes"]]
            total_v += len(vs)
            if p["variants"]["pageInfo"]["hasNextPage"]:
                over25 += 1
            out.append({"gid": p["id"], "variants": vs})
        print(f"\r  {total_p} products / {total_v} variants", end="", flush=True)
        if not prods["pageInfo"]["hasNextPage"]:
            break
        cursor = prods["pageInfo"]["endCursor"]
    json.dump(out, open(CACHE, "w"))
    print(f"\n缓存 -> {CACHE}（{total_p} 产品 / {total_v} 变体；变体>25 的产品 {over25} 个已记录）")


def build_plan():
    prods = json.load(open(CACHE))
    plan, skip_ok, skip_zero, skip_odd, rewrite_bad = [], 0, 0, 0, 0
    buckets = {"15-18%": 0, "18-22%": 0, "22-25%": 0}
    samples = []
    for p in prods:
        items = []
        for vid, price, cap in p["variants"]:
            if cap and Decimal(cap) > Decimal(price):  # 有效既有锚价（>现价）：保留
                skip_ok += 1
                continue
            if cap:
                rewrite_bad += 1  # 倒挂/零值脏数据：纳入重写
            a, note = anchor_for(price)
            if not a:
                if note.startswith("price<=0"):
                    skip_zero += 1
                else:
                    skip_odd += 1
                continue
            items.append({"gid": vid, "compareAtPrice": a})
            d = float(note.rstrip("%"))
            buckets["15-18%" if d < 18 else "18-22%" if d < 22 else "22-25%"] += 1
            if len(samples) < 12:
                samples.append((vid.split("/")[-1], price, a, note))
        if items:
            plan.append({"pid": p["gid"], "variants": items})
    json.dump(plan, open(PLAN, "w"))
    n_w = sum(len(x["variants"]) for x in plan)
    lines = [
        "# 全店划线价 dry-run（未写入任何数据）",
        f"- 拉取: {len(prods)} active 产品",
        f"- 计划写入: {len(plan)} 产品 / {n_w} 变体（含倒挂脏数据重写 {rewrite_bad}）",
        f"- 跳过: 有效既有锚价 {skip_ok} / price<=0 {skip_zero} / 折扣异常 {skip_odd}",
        f"- 折扣分布: {buckets}",
        "", "## 样例（variant_id, price → compare_at, discount）",
    ] + [f"- {s[0]}: {s[1]} → {s[2]} ({s[3]})" for s in samples]
    open(REPORT, "w").write("\n".join(lines))
    print(f"plan -> {PLAN}（{len(plan)} 产品 / {n_w} 变体，倒挂重写 {rewrite_bad}）；报告 -> {REPORT}")
    print("跳过: 有效锚价", skip_ok, "| price<=0", skip_zero, "| 异常", skip_odd, "| 分布", buckets)


def apply(limit=None):
    plan = json.load(open(PLAN))
    try:
        done = {json.loads(l)["pid"] for l in open(DONE) if l.strip()}
    except FileNotFoundError:
        done = set()
    todo = [x for x in plan if x["pid"] not in done]
    if limit:
        todo = todo[:limit]
    print(f"待写 {len(todo)} 产品（断点已含 {len(done)}）")
    ok_p = ok_v = err = 0
    t0 = time.time()
    with open(DONE, "a") as fdone:
        for i, p in enumerate(todo, 1):
            try:
                r = gql(MUT, {"pid": p["pid"], "vs": [
                    {"id": v["gid"], "compareAtPrice": v["compareAtPrice"]} for v in p["variants"]]})
                ue = r["productVariantsBulkUpdate"]["userErrors"]
                if ue:
                    err += 1
                    print(f"\n[UE] {p['pid']}: {ue}")
                else:
                    ok_p += 1
                    ok_v += len(p["variants"])
                fdone.write(json.dumps({"pid": p["pid"], "ok": not ue}) + "\n")
                fdone.flush()
            except Exception as e:
                err += 1
                print(f"\n[EXC] {p['pid']}: {e}（跳过，可重跑续传）")
            if i % 50 == 0:
                rate = i / (time.time() - t0)
                print(f"  进度 {i}/{len(todo)} | 成功 {ok_p} 产品/{ok_v} 变体 | 错误 {err} | {rate:.1f}/s", flush=True)
    print(f"\n完成: 成功 {ok_p} 产品 / {ok_v} 变体 / 错误 {err}（含断点累计 {len(done) + len(todo)}）")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dryrun"
    {"fetch": fetch, "dryrun": build_plan, "apply1": lambda: apply(limit=1), "apply": apply}[cmd]()
