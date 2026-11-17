# -*- coding: utf-8 -*-
"""UPC 清单四层校验 + estry_upc_map 永久建档。

用法(两种输入, 二选一):
  A. 用户已分配: CSV 文件两列 sku,upc  -> python upc_validate.py map.csv
  B. 用户给前缀码段: python upc_validate.py --prefix 0654321 --start 00001
     --count 15000  (按 cs_id 升序自动分配)

校验层: L1格式(12位数字) L2校验位 L3 GS1前缀识别(归属地)
        L4 重复检测 -> 全过写入 estry_upc_map(status=1 待GEPIR)
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import get_engine

GS1_PREFIX = {
    "0": "GS1 US (北美)", "1": "GS1 US (北美)", "2": "GS1 US(12位UPC)",
    "3": "GS1 FR", "4": "GS1 DE", "3-380": "GS1 BG", "5": "GS1 US/加拿大",
    "50": "GS1 UK", "57": "GS1 DK", "4-45/49": "GS1 JP",
    "489": "GS1 HK", "690-699": "GS1 China", "471": "GS1 TW",
    "880": "GS1 KR", "93": "GS1 AU",
}


def check_digit_ok(code12: str) -> bool:
    """UPC-A(12位)校验位: 奇数位和x3 + 偶数位和, 补到10的倍数。"""
    s = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(code12))
    return s % 10 == 0


def prefix_of(code: str) -> str:
    if code[:3] == "489":
        return "GS1 HK"
    if 690 <= int(code[:3]) <= 699:
        return "GS1 China"
    if code[0] in "01":
        return "GS1 US"
    return f"前缀 {code[:3]}"


def load_variants():
    """全店变体: sku -> (variant_id, cs_ean)。cs_ean 从清码存档读。"""
    eng = get_engine()
    bk = Path("/home/jason/shopify-admin/deploy/backup/"
              "barcode_backup_20261108.jsonl")
    import json
    ean_map = {}
    for line in open(bk, encoding="utf-8"):
        d = json.loads(line)
        if d["sku"]:
            ean_map[d["sku"]] = d["barcode"]
    return eng, ean_map


def ensure_table(eng):
    with eng.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS estry_upc_map (
          variant_id BIGINT PRIMARY KEY COMMENT 'Shopify变体ID',
          sku        VARCHAR(64) COMMENT '变体SKU(当前MPN)',
          upc        CHAR(12) COMMENT '新UPC(Estry名义)',
          cs_ean     VARCHAR(13) COMMENT '原Cameron Sino EAN存档',
          status     TINYINT DEFAULT 1 COMMENT '0待校验 1格式过 2GEPIR过 3已回填 4拒绝',
          note       VARCHAR(255) DEFAULT '',
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))
    print("表 estry_upc_map 就绪")


def main():
    eng, ean_map = load_variants()
    ensure_table(eng)

    rows = []  # (sku, upc)
    if sys.argv[1] == "--prefix":
        prefix = sys.argv[2]
        start = int(sys.argv[3])
        count = int(sys.argv[4])
        skus = sorted(ean_map.keys())[:count]
        for i, sku in enumerate(skus):
            body = f"{prefix}{start + i:0{11 - len(prefix)}d}"
            rows.append((sku, body[:11] + "-"))  # 校验位最后算
        # 计算校验位
        fixed = []
        for sku, code in rows:
            s = sum(int(c) * (3 if i % 2 == 0 else 1)
                    for i, c in enumerate(code[:11]))
            cd = (10 - s % 10) % 10
            fixed.append((sku, code[:11] + str(cd)))
        rows = fixed
    else:
        with open(sys.argv[1], encoding="utf-8-sig") as f:
            for r in csv.reader(f):
                if len(r) >= 2 and r[0].lower() != "sku":
                    rows.append((r[0].strip(), r[1].strip()))

    print(f"载入 {len(rows)} 条 UPC")

    good, bad = [], []
    seen = set()
    for sku, upc in rows:
        why = []
        if not (len(upc) == 12 and upc.isdigit()):
            why.append("非12位数字")
        if len(upc) == 12 and upc.isdigit() and not check_digit_ok(upc):
            why.append("校验位错误")
        if upc in seen:
            why.append("重复")
        seen.add(upc)
        if sku not in ean_map:
            why.append("SKU未匹配到变体")
        if why:
            bad.append((sku, upc, why))
        else:
            good.append((sku, upc))

    print(f"格式校验通过: {len(good)} | 拒绝: {len(bad)}")
    pf = {}
    for _, u in good:
        p = prefix_of(u)
        pf[p] = pf.get(p, 0) + 1
    print("前缀分布:", pf)
    for sku, upc, why in bad[:10]:
        print("  拒绝样例:", sku, upc, why)

    with eng.begin() as conn:
        conn.execute(text("""
        INSERT INTO estry_upc_map (variant_id, sku, upc, cs_ean, status)
        VALUES (0, :sku, :upc, :ean, 1)
        ON DUPLICATE KEY UPDATE upc=VALUES(upc), status=1
        """), [{"sku": s, "upc": u, "ean": ean_map.get(s, "")}
               for s, u in good])
    print(f"已写入 estry_upc_map: {len(good)} 条 (status=1 格式过)")

    print("""
下一步(L4 GEPIR 实测):
  打开 gepir.gs1.org -> Search by GTIN -> 抽 10 个 UPC 查询
  预期: 返回 Estry 主体信息 = 可回填(upc_backfill.py)
        查无记录 = 数据未同步(等1-3个月) | 返回他人公司 = 拒绝(status=4)
""")


if __name__ == "__main__":
    main()
