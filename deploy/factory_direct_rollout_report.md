# 全店推广交付报告 — Factory Direct 最低价体系（2026-11-18 凌晨，无人值守授权执行）

## 你睡觉时发生了什么

按你的授权（"全店推广，后续操作不要我批准"），完成两件事：

## ① Factory Direct 区块进默认模板（全店产品页生效）

- `templates/product.json`：`price` 之后插入 `fd_note` block（`factory_direct` 类型）
- **效果：全店 4839 个在线产品页**价格区下方自动显示 Factory Direct — Lowest Official Price 卡片
- 样板产品已切回默认模板（单一来源，专属模板 `product.factory-direct.json` 保留但不再引用）
- 改动前备份：`deploy/backups/20261118_*__templates__product.json`

## ② 全店批量划线价（GraphQL 逐产品批量，断点续跑，0 错误）

公式：`compare_at = price × 1.18 → .99 心理价`（折扣 15~25% 区间，超 25% 退精确值）

| 波次 | 对象 | 产品/变体 | 结果 |
|---|---|---|---|
| 第一波 | 未设锚价的变体 | 1790 / 1886 | 全部成功 |
| 第二波 | **倒挂脏数据**（cap ≤ price，前台不渲染） | 3027 / 3514 | **完成：3026 产品 / 3513 变体，0 错误** |
| 保留 | 有效既有锚价（>现价的真促销） | 29 变体 | 未动 |
| 跳过 | price≤0 | 1 | — |

**重要发现**：拉取时发现 3541 个变体（65%）的既有锚价是倒挂脏数据（≤现价或 0），前台根本不显示——这解释了此前全店只有单价显示。第二波已全部用公式重写。

覆盖：**~5400/5428 变体 = 99.5% 全店**（唯一例外 1 个 price≤0 占位变体）

## 验证证据

- GraphQL/REST 回读抽检：第一波 3/3 + 第二波 3/3 全通过（25.99→30.99、23.99→28.99、20.59→24.99 等）
- 前台渲染（playwright 双端）：
  - 样板页（默认模板）：~~$22.99~~ → **$18.99** + Sale 徽章 + Factory Direct 区块 ✓
  - Foxlink 普通产品页：~~$48.99~~ → **$40.99** + Factory Direct 区块 ✓（Sold out 页无回归）
  - 截图：`verify_foxlink.png` / `verify_foxlink_mobile.png` / `verify_lefant.png`
- console 0 新增错误

## 回滚方式（如需）

- 区块：恢复 `deploy/backups/20261118_*__templates__product.json`
- 划线价：`rollout_compare_at.py` 的 plan/done 文件可反向清空（变体 compareAtPrice 置 null）；单产品后台手动清除亦可

## 遗留观察项（未做，等你醒来定）

1. 公告栏 "Factory Direct — Lowest Official Price" 横幅 + FAQ "Why cheaper than marketplaces" 条目（原预案配套项，未授权不动）
2. GA4 观测：7 天 view_item→begin_checkout 转化对比（对比样板期基线）
3. 出现 1 个 404 产品（battery-for-lefant-m1...，API active 但未发布在线渠道）——属历史渠道状态问题，与本次改动无关
4. 部分产品变体 2200mAh 等显示 Sold out——库存策略问题，与本次无关

## 文件清单（服务器 /home/jason/shopify-admin/deploy/）

- `rollout_compare_at.py`（fetch/dryrun/apply1/apply，幂等可续跑）
- `rollout_dryrun.md`（第二波差异预览）
- `rollout_apply.log` / `rollout_apply2.log`（执行日志，含进度与错误）
- `rollout_done.jsonl`（断点记录）
- `audit_existing_ca.py`（既有锚价审计：3512 倒挂 / 29 有效）
- `verify_rollout.py`（REST 回读抽检）
