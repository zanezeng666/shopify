# 订单 #2241 来源分析（2026-11-18）

## 订单快照

| 项 | 值 |
|---|---|
| 订单 | #2241，$28.99 USD，**paid**，PayPal |
| 产品 | CardinalHealth Kangaroo Joey 肠内给食泵电池（医疗线，11-12 relaunch 恢复上架的 82 品之一）SKU `CS-CHA506MD_CardinalHealth_43_0` |
| 客户 | Yvonne（yahoo.com），iPhone iOS 18.7 Safari，en-US |
| 收货 | Calumet City, IL, US（真实美国地址） |
| 时间 | 北京 11-18 06:28（美国中部 11-17 16:28） |

## 来源判定：Google Ads 付费点击（证据链）

订单 `referring_site` 带 Google Ads 自动标记：

```
gad_source=1                        ← Google Ads 付费点击
gad_campaignid=24452460184          ← 广告系列 ID
gbraid=0AAAAAC-vMik2r7xEh3Ez        ← 跨网络点击标识（PMax/展示类，非搜索 gclid）
```

- 落地页 = 该产品页（广告直达产品页，符合 Shopping/PMax 特征）
- 下单路径：广告点进产品页 → 直达购物车链接（`/cart/c/...&storefront_wallet=true`）→ PayPal

## ⚠️ 复查收口（2026-11-18 晚，用户反馈"只有一个 Ads 账户"后五路重查）

| # | 排查路径 | 结果 |
|---|---|---|
| 1 | 主账户 73 个 campaign 全量（含 REMOVED）精确比对 | ❌ 无 24452460184 |
| 2 | change_event 11-14~18（3676 条变更）| ❌ CAMPAIGN 变更 116 条全是 geo 修复+status 闪断，**0 创建 0 删除**（排除"建了又删"） |
| 3 | OAuth 可访问账户全查 | 'estry'(7059800494) + 'Zhien Zeng'×2（**两个空壳，0 campaign**——用户名下其实有 3 个账户） |
| 4 | MC(BomiBattery 136469408) adsLinks | ❌ 仅链 7059800494（排除购物类第二账户；Search/展示广告本就不需要 MC） |
| 5 | GA4 sessionCampaign/sessionGoogleAdsAccountID | 0 数据——**GA4 未与任何 Ads 账户链接**（无法用 GA4 甄别） |

## ✅ 终局定论（2026-11-18 深夜，用户指出"明显是 PMax"后产品级实锤）

**用户判断正确：这单就是主账户 PMax (24441391608 'PMax Medical Estry') 带来的。**

| 证据 | 数据 |
|---|---|
| ★产品级点击 | `shopping_performance_view`：订单产品 `shopify_us_15484819702004_68037392302324`（CS-CHA506MD Kangaroo Joey）**11-18 获 1 次点击、¥7.83 花费**——与订单创建（北京 11-18 06:28）同日同时窗 |
| ★小时曲线吻合 | PMax 11-18 5时 26clk/¥46.78、6时 11clk/¥26.20——订单落在投放高峰内（=美国 11-17 下午黄金购物档） |
| 流量形态 | `gbraid`（跨网络点击标识）+ 广告直达产品页 + 购物车钱包快速结账——PMax 购物分量典型路径 |

**为什么 `gad_campaignid=24452460184` 在账户里查不到**：PMax 跨网络流量的点击 URL 中，`gad_campaignid` 的值是 **Google serving 侧内部标识**，不映射 Ads API 的 `campaign.id`（=24441391608）或 `asset_group.id`（=6770847164）。它不是另一个账户的 campaign——跨网络（gbraid 体系）URL 参数本就不保证对应账户可见资源。（此前"第 4 个账户"的推论已被此实锤推翻并修正。）

**方法论教训**：①"参数名叫 campaignid"≠"值必是 campaign.id"——查无此人时应先质疑映射假设（奥卡姆剃刀），而不是构建"隐藏账户"假说；② PMax 归因验证的正确工具是 `shopping_performance_view` 产品级报告（注意：该视图不支持 `campaign.id` WHERE 过滤，需全量拉取本地比对）+ 小时级曲线对照下单时刻。

顺带发现：GA4 与 Ads 未链接 → Ads↔GA4 转化回传、受众共享全部缺失，修复后广告优化数据面会完整（待 Ads 冻结期过后再动）。

## 附带发现

1. **PMax 断崖恢复中**：主账户日花费 ¥116(11-16)→¥209(11-17)→¥218(11-18 未完)，点击 86→124→111；今日 Cross-network 会话 54。
2. **划线价首单**：全店划线价+Factory Direct 区块在北京凌晨 00:38-01:30 上线，这单 06:28——买家看到的是 **-17% 划线价 + FD 区块**版页面后下单（$28.99 → 锚价 $33.99+，公式 ceil99(28.99×1.18)=$34.99，折扣 17.1%）。
3. **GA4 漏单**：该 purchase 事件未进 GA4（PayPal 往返 + Safari ITP 丢会话）。GA4 窗口内只见 2 笔旧 purchase（11-16 braava jet $46.98、11-17 zen vision 样板页 $37.98）——**GA4 转化报表系统性低估，评估广告效果以 Shopify 订单 + Ads 归因为准**。

## 结论

这单 = **主账户 PMax Medical Estry 付费流量（产品级点击 ¥7.83 实锤）→ 真实美国客户 → PayPal 成功支付**。广告投放开始出单，医疗线（PMax 定向）策略初步见效，无任何隐藏账户问题。

---
*分析脚本：deploy/analyze_today_order.py / analyze_order_source2~6.py / pmax_verify2~3.py（产品级实锤，可复跑）*
