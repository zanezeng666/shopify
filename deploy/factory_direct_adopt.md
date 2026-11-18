# Factory Direct 最低价信任体系 — 样板交付记录（2026-11-17）

## 样板页

https://www.estrybattery.com/products/battery-for-creative-zen-vision-m-zen-vision-m-video-ba20603r79914-dvp-hd0003
（近 3 单 ChatGPT feed 出单型号之一，$18.99 / 变体 1700mAh）

## 已生效改动（4 项）

| # | 改动 | 内容 | 回滚 |
|---|------|------|------|
| 1 | variant 32058744176740 | compare_at_price=$22.99（18.99×1.18→.99 心理价，展示 -17%） | `set_compare_at_sample.py clear` |
| 2 | sections/main-product.liquid | schema 注册 `factory_direct` block 类型 + when 分支（卡片式叙事区块，含内联样式） | 恢复 `deploy/backups/20261117_2356__sections__main-product.liquid` |
| 3 | templates/product.factory-direct.json | 新模板，fd_note block 紧跟 price block | 删除该资产即可 |
| 4 | product 4638608261220 | template_suffix=factory-direct（仅此产品可见新区块，默认模板未动） | template_suffix 置空 |

前台价格渲染链（主题原生，未改动）：price.liquid 自动渲染 "Regular price ~~$22.99~~ → Sale price $18.99 + Sale 徽章"；集合卡片 card-product.liquid 同步支持 Sale badge。

## 合规红线（已执行）

全站文案不出现 Amazon/eBay/Walmart 字样；划线价不注明来源；叙事仅表述 "Marketplaces charge ~15% in seller fees"。

## 验收证据

- 桌面 1440：`fd_desktop.png` + `fd_verify_desktop.yml`（L74-85：划线价/Sale 徽章/Factory Direct 区块顺序正确）
- 移动 390：`fd_mobile.png` + `fd_verify_mobile.yml`（L52-63：同样正常）
- console 错误均为既有无关项（shop.app CSP / googleadservices 网络问题），无新增

## 全店推广预案（待用户确认后执行，dry-run 先行）

1. **批量划线价**：全店在售 SKU `compare_at = price × 1.18 → .99`（GraphQL bulk；脚本 `rollout_compare_at.py --dryrun` 先出差异预览：SKU/现价/锚价/折扣%）
2. **默认模板接管**：把 factory_direct block 加入默认 templates/product.json（全店产品页显示叙事区块，替代 per-product 模板）——需二次确认
3. **配套**：公告栏追加 "Factory Direct — Lowest Official Price"、FAQ 增 "Why are your prices lower than marketplaces?" 条目
4. **观测**：GA4 7 天转化对比（view_item → add_to_cart → begin_checkout），参照样板页基线

## 相关文件

- `deploy/set_compare_at_sample.py`（划线价写/清）
- `deploy/add_factory_direct.py`（区块交付，幂等可重跑，dry-run 默认）
- `deploy/fix_ui_quote_fd.py`（11-18 UI 修复：① Bulk Quote 按钮默认态白字——原 `color:#1B2A41;background:#1B2A41` 黑底黑字笔误 → `color:#fff`；② fd-note 排版 0.72/0.86rem+全大写 → 0.95rem 正常句式，对齐主题正文）
- `deploy/backups/20261117_2356__*`、`20261117_2357__*`、`20261118_*`（改动前备份）
