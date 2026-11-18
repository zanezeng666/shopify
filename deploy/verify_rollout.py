"""抽检（REST 直查）：第一波+第二波写入的变体回读 + 输出产品 URL 供前台验证。只读。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client
plan = json.load(open("/tmp/ca_plan.json"))
done_pids = {json.loads(l)["pid"] for l in open("/home/jason/shopify-admin/deploy/rollout_done.jsonl") if l.strip()}
# 抽 3 个：已完成（第一波断点里的）×2 + 第二波 plan 中段 ×1
done_sample = [x for x in json.load(open("/tmp/ca_plan.json")) if x["pid"] in done_pids][:0]  # plan 已换新，改从历史抽
# 第一波产品 = 第二波 plan 之外 + done 里的 —— 简化：直接抽 3 个变体 id 均匀取样
all_done = []
for l in open("/home/jason/shopify-admin/deploy/rollout_done.jsonl"):
    if l.strip():
        all_done.append(json.loads(l)["pid"])
# done 文件只有 pid，变体要从缓存映射
pid2var = {}
for p in json.load(open("/tmp/ca_products.json")):
    pid2var[p["gid"]] = p["variants"]

picks = [all_done[5], all_done[len(all_done) // 2], all_done[-3]] if len(all_done) > 5 else all_done[:3]
for pid in picks:
    vs = pid2var.get(pid) or []
    if not vs:
        print(f"[?] {pid} 无缓存变体")
        continue
    vid, price, _ = vs[0]
    num = vid.split("/")[-1]
    v = c.request("GET", f"variants/{num}.json")["variant"]
    pid_num = v["product_id"]
    pr = c.request("GET", f"products/{pid_num}.json", params={"fields": "handle"})["product"]
    print(f"variant {num}: price={v['price']} compare_at={v.get('compare_at_price') or v.get('compare_at')}")
    print(f"  -> https://www.estrybattery.com/products/{pr['handle']}")
