# Estry B2B 一期交付说明（2026-11-13）

## 上线清单（全部已生效）

| 页面 | URL | 说明 |
|---|---|---|
| 专业搜索页 | /pages/battery-search | 8,752 型号全量索引，五维分面（品类/设备品牌/化学体系/电压/容量），关键字即时过滤（型号/设备/OEM件号），结果规格表格+分页，行内 Specs/Buy 按钮 |
| 规格书页 | /pages/specification?m=CS-XXXXXX | 单型号完整 datasheet：电气/机械参数表、OEM 件号与兼容设备 chips、认证区、A4 print CSS（Print/PDF 按钮） |
| 询盘页 | /pages/wholesale | 原生 contact form：公司/联系人/邮箱/国家/型号清单(多行)/数量/目标价/需求类型(报价/规格书/证书/样品)，`?sku=` 自动预填，`?need=certs|spec` 自动勾选 |
| 证书页 | /pages/certificates | UN38.3/MSDS/CE/RoHS/IEC 62133/运输文件 六卡 + 三步索取流程 → 询盘页联动 |
| 入口贯通 | — | 产品页价格区下方 View Full Specs / Bulk Quote 双按钮（读变体 SKU 动态构造链接）；首页 hero 搜索提交跳 /pages/battery-search |

## 数据链路

镜像库(active CS 变体) × cs_new.cs_product --JOIN--> `build_spec_index.py` --> spec-idx-manifest.json + spec-idx-{0,1,2}.json (theme assets, ~3.9MB) --> 前端 fetch 内存筛选 (<50ms)。

## 日常运维 SOP

**索引更新（新品/改价后）**：
```
cd /home/jason/shopify-admin
sudo -u jason env HOME=/home/jason .venv/bin/python deploy/build_spec_index.py
```
全量重建+分片幂等重传（先删旧分片），输出字段填充率审计。asset 上传后 CDN `?v=` 参数自动变化，无缓存问题。

**全量回归验证**：
```
sudo -u jason env HOME=/home/jason .venv/bin/python deploy/verify_b2b_pages.py
```
覆盖四页元素、manifest CDN、样本规格书、ACTIVE 产品双按钮、首页入口。

**脚本族（均幂等可重跑）**：
- `build_spec_index.py` 索引构建
- `add_battery_search.py` 搜索页（section estry-battery-search.liquid + 模板 + 页面）
- `add_spec_sheet.py` 规格书页（estry-spec-sheet.liquid）
- `add_inquiry_cert.py` 询盘+证书页（estry-wholesale / estry-certificates.liquid）
- `add_b2b_entry.py` 入口注入（--probe 查锚点；main-product/hero 注入前自动备份 /tmp/main-product.bak-*）

**回滚**：main-product.liquid / estry-search-hero.liquid 备份在服务器 /tmp/*.bak-*（重传原文件即可）；四个 section 重传上一版本内容。

## 已知事项

1. **主导航 Wholesale 项未自动添加**——menus/link_lists API 对当前 token 403（无权限）。后台手动：Online Store → Navigation → Main menu → Add item → 页面 Wholesale（30 秒）。
2. **Buy 1 pc 链接指向 draft 产品会 404**——索引按 CS 目录构建，含部分已下架产品（2026-11-12 全量下架后远端 ACTIVE 4,284）。规格书页 Buy 按钮对无 handle 型号自动隐藏；有 handle 但 draft 的仍会 404，属可接受损耗（重跑 build_spec_index 可按需收紧口径）。
3. **镜像 products.status 失真**——验证/取样的产品状态以远端 products.json 为准（verify 脚本已如此实现）。
4. **询盘送达**——contact form 直达商店后台邮箱，无额外后端；需求类型/型号清单以字段形式进邮件正文。

## B2B 二期/三期路线（询盘量验证后启动）

**二期**：批发价体系——密码保护批发区、阶梯价/MOQ 表、草稿订单人工开发票（Shopify Draft Order API）、询盘→报价→订单转化漏斗看板。
**三期**：客户档案与账期——B2B 客户分组专属价目表、NET30 账期审批流、复购快速下单（复用 ae-supply 供应商门户的角色/欠款模型反向构建）。
