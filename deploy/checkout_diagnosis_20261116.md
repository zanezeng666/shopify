# 结账断点诊断报告（2026-11-16）

漏斗异常：add_to_cart 255 → begin_checkout 264 users → add_shipping_info **1** → add_payment_info 0 → purchase 0

## ★★ 2026-11-16 晚重大数据修正（GA4 16 天全窗 + Shopify 订单核验，用户质疑"264 检验论"后重查）

**之前"8 天 0 转化"是时间窗口口径假象；"连连被检验 264 次全失败"是过度归因，正式撤回。**

GA4 全窗（11-01~11-16）真实漏斗与订单核验：

| 事件 | users | 备注 |
|---|---|---|
| begin_checkout | 637 | **China 472 (74%) / US 40 (6.3%) / Brazil 19 / SG 11 / DE 10...** |
| add_shipping_info | 3 | 断点主段：begin→shipping 流失 99.5% |
| add_payment_info | 2 | 到达支付选择的仅 2 人 |
| purchase | 2 | **都是 US 用户，100% 转化（到达支付环节者零流失）** |

Shopify 订单（transactions.json 核验 gateway）：

| 订单 | 时间 | 金额 | 状态 | 通道 |
|---|---|---|---|---|
| #2239 | 11-15T11:27(UTC-12) | $46.99 | paid | **paypal** |
| #2238 | 11-06T10:38 | $33.99 | paid | **paypal** |
| #2237 | 10-29 | $39.72 | refunded | paypal |
| #2236 | 10-16 | $29.99 | paid | paypal |
| #2235 | 10-03 | $15.25 | paid | paypal |

**修正后结论：**
1. **店铺不是 0 单**：约每 1-2 周一单，全部走 **PayPal**（历史 5 单无一例外）；连连 **0 单**
2. **连连几乎从未被测试**：16 天仅 2 人到达支付选择环节（都成了 PayPal 单）——没人选中过连连，"连连接不住用户"缺乏数据支撑，它只是没出场机会
3. **真实断点在 begin_checkout→add_shipping_info（99.5% 流失）**，在用户面对支付方式做出选择**之前**；且 begin_checkout 74% 是中国流量（爬虫/自查/污染），真实美国进结账用户仅 ~40 人/16 天 → **上游流量量级才是第一矛盾**（11-16 起 PRESENCE 修复后干净口径：11-16 begin_checkout 已降至 10 users）
4. US 口径换算：40 人进结账 → 2 单 = 5% 结账转化率，对小流量新店属正常区间——支付环节本身不是 0，是被流量饥饿掩盖
5. 连连在 Shopify 的集成模式（官方文档实锤）：仅支持**收银台跳转式**；iframe/Direct API 模式的支持平台列表里没有 Shopify → **跳转形态在连连侧无解**
6. 连连口碑（网络检索）：买家侧品牌认知度低、公开评论情绪偏负面（PureVPN：*"many users don't recognize the brand... overall sentiment is mostly negative"*，多源于对陌生品牌的不信任）；卖家侧收款合规牌照齐全口碑尚可（中文渠道为主）。**买家侧信任劣势真实存在但未被本店数据检验**

**修正后的行动含义：**
- PayPal 是唯一被本店数据验证的收款通道 → 开启 PayPal guest checkout（卡用户出口）优先级不变且加强
- 连连去留不再有"市场检验失败"的指控依据，但其首屏 40+ 钱包列表减分仍在 + Shopify 上无内嵌方案 → 建议：guest checkout 开启后 A/B 观察或直接移除简化首屏
- 上游流量（美国真实买家进结账量）才是第一优先

---


## 一、GA4 数据（11-08 ~ 11-15，近 8 天）

| 事件 | events | users | sessions |
|---|---|---|---|
| view_item | 28,625 | 28,165 | 28,154 |
| add_to_cart | 255 | 255 | 254 |
| begin_checkout | 280 | **264** | 264 |
| add_shipping_info | 9 | **1** | 2 |
| add_payment_info | 0 | 0 | 0 |
| purchase | 0 | 0 | 0 |

- 断点形态：264 人进结账 → **仅 1 人走到"选运费"**（且该用户重试 9 次 = 反复尝试走不通后放弃）
- add_to_cart(255) < begin_checkout(264)：25 差值来自 PDP 直接进结账/事件丢失，非核心矛盾

## 二、浏览器真实走查（美国加州地址 1600 Amphitheatre Pkwy, Mountain View, CA 94043）

### 正常项 ✓

- 结账页正常打开（www.estrybattery.com/checkouts，"Estry Checkout" 品牌化生效）
- 表单可填写；国家/州 zone 校验正常（切换时报错消失属正常交互）
- 运费在 ZIP+State 填完后 ~8s 内出现
- **美国免邮生效：Shipping = FREE，Total = $24.99**（无运费惊吓问题）
- 页脚政策四链接在位（Refund/Privacy/Terms/Shipping）

### 断点项 ✗

**P0-1 支付体验崩坏（核心断点）**——One-page checkout 支付区**首屏可见**，用户进结账第一眼看到：

- **PayPal 默认选中**（radio checked=true）——非 PayPal 用户第一眼即劝退
- 唯一"卡"支付 = "**Cards and Local Payment Methods**"（第三方 PSP 跳转式）：
  - 选中后提示 *"You'll be redirected to ... to complete your purchase"*——**无内嵌卡号表单，跳外站**
  - 名称下挂 40+ 亚洲/拉美钱包（pix/grabpay/dana/alipay/wechatpay/kakao_pay...），对美国医疗采购用户零信任感
  - **PSP 实为连连支付（LianLian Pay），2026-11-16 二次走查实锤**（加州地址全流程走通至跳转页）：
    - 跳转页 `secure-checkout.lianlianpay.com`，页内确有信用卡表单（卡号/有效期/CVV），技术上可刷卡（含 discover/diners/jcb/unionpay + afterpay）
    - ★**语言结论修正（同日 en-US 复测）**：连连收银台语言跟随浏览器自动检测——zh-CN 浏览器→中文界面（首次走查误判为"默认中文"），**en-US 浏览器→全英文界面**（Secure Checkout / Pay with card，语言下拉自动选中 English，截图 deploy/lianlian_redirect_enUS.png）。美国用户看到的不是中文收银台
    - 真实剩余减分项（修正后）：①Shopify 结账页入口挂 40+ 亚洲/拉美钱包名的展示（Shopify 侧渲染，连连改不了）②跳转离开 Shopify 到陌生域名（第三方 PSP 共性，PayPal 例外——品牌信任高）③无 APay/GPay/Shop Pay。跳转页本身（英文+卡表单）可用
    - 结论：**通道真实、英文可用、减分项比初判轻**；264 进结账 0 转化的主因是支付区首屏呈现（PayPal 默认+钱包列表杂乱+无钱包）导致的**跳转前**流失
    - 截图：deploy/lianlian_redirect_page.png（zh 环境）/ lianlian_redirect_enUS.png（en-US 真实态，权威）
- **无 Shop Pay / Apple Pay / Google Pay**——美国主流钱包全缺
- Express checkout 区只有 PayPal 一个按钮

→ 根因：**店铺未激活 Shopify Payments（美国区）**。定价模型的收款成本假设（Shopify Payments 2.9%+$0.30）实际未成立。

**P1-1 Local delivery 泄漏到美国地址**——配送方式 2 个：Local delivery（**默认选中**！）+ Standard Shipping (3-6 business days)。美国加州地址不应出现"本地配送"，疑为香港本地配送 zone 配置覆盖过宽。用户困惑 + 若被选中存在无法履约风险。

**P2-1 信任要素薄弱**——0 评论新店 + 政策链接仅在页脚小字；无保修承诺展示（替换电池买家第一大顾虑）。

## 三、断点定位逻辑

One-page checkout 中支付区块无需填地址即首屏可见 → 用户进入结账页（触发 begin_checkout）→ 第一眼看到"PayPal 默认 + 杂牌跳转卡支付 + 无钱包" → **在填地址前直接流失** → 完美解释 264 → 1 的断崖。唯一走到选运费的用户在支付跳转环节也放弃了（add_payment_info=0）。

## 四、修复清单（按优先级）

| # | 动作 | 优先级 | 执行方 |
|---|---|---|---|
| 1 | **激活 Shopify Payments（US 区）**：内嵌卡表单 + Shop Pay 自动可用。需店铺后台身份/银行验证 | P0 | 需用户在 Shopify Admin 操作（AI 无法代办） |
| 2 | Shopify Payments 激活后：调整支付方式顺序（Shop Pay/卡置顶，PayPal 非默认） | P0 | 激活后 AI 可做 |
| 3 | 修复 Shipping zone：Local delivery 限制香港本地；美国仅留 Standard Shipping（免邮） | P1 | AI 可查（shippingAndDeliverySettings GraphQL / Admin 后台） |
| 4 | 政策页补全 + 结账页脚展示（Shipping/Refund/Warranty） | P2 | 本计划下一项 |
| 5 | 复查：修复后 7 天观察 begin_checkout → add_payment_info 流向 | 验证 | ads_watch 已含关键事件 |

## 五、遗留观察

- 修复 #1/#2 后，支付转化按行业基准（结账转化 30-60%）264 进结账用户量级可期月增数十单
- 走查截图：deploy/checkout_step_shipping_wait.png（运费等待态）、checkout_step_payment.png（支付区状态）
- GA4 查询脚本：deploy/checkout_funnel_ga4.py（可重跑）
