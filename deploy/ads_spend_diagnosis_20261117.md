# Google Ads 花费断崖归因报告（2026-11-17）

## 现象
- 11-15：¥627（PMax ¥380 + Search ¥240）正常
- 11-16：¥116（Search 全天零花费，仅 PMax 上午花 ¥88，14:00 起停）
- 11-17：全天 ¥5，美东黄金时段零消耗

## 排除项（全部核验）
| 嫌疑 | 核验结果 |
|---|---|
| 余额耗尽 | ❌ 用户确认 ¥2800 在账 |
| campaign 被停/拒 | ❌ 40 个全部 ENABLED/SERVING |
| 地理定向错 | ❌ 41 个 campaign 全部 = United States(US) |
| 预算异常 | ❌ PMax ¥300/日、Search ¥50/日正常，无共享预算 |

## 真因：四重学习期打击叠加（change_event 权威时间线，账户时区=北京时间）

| 时间 | 操作 | 来源 |
|---|---|---|
| 11-15 21:08 | PMax 预算调整为 ¥300/日 | 用户侧 |
| 11-15 21:26~21:38 | **PRESENCE 地理修复**（40 campaign，PRESENCE_OR_INTEREST→PRESENCE） | AI 会话（ads_presence_all.py） |
| 11-16 07:52 | PMax 素材文字更新（ASSET） | 用户侧 |
| 11-16 12:04~12:10 | 批量 campaign 暂停 6 分钟又恢复（工具闪断）+ **3552 个关键词 BROAD→PHRASE** | 用户侧（2026-11-17 用户确认） |

## 机制
1. **PRESENCE 修复砍掉 INTEREST 流量池**：修复前 cpc 流量仅 21% 美国，南亚/中东 ~45% 全靠 INTEREST 匹配。改 PRESENCE 后该池瞬间蒸发 → Search 自 11-16 00:00 起零展示（紧贴 11-15 晚修复）
2. **BROAD→PHRASE 进一步收窄**：改词理由（大词无效）成立的前提是南亚池存在；PHRASE + 美国池 + ¥50/日小预算 + 低质量分 → 几乎竞不到展示
3. **PMax 被打了三针**（PRESENCE + 素材更新 + 暂停闪断），每动一次重置一次学习期 → 11-16 14:00 起彻底保守
4. Search 断崖在前（11-16 00:00）、PMax 断崖在后（14:00），时间线与各自触发点吻合

## 结论
¥5/日是学习期异常态，非稳态。纯美国池合理稳态预估：PMax ¥90-180/日（预算 30-60%），Search 逐步回血但受 PHRASE 收窄约束。

## 处方
1. **冻结一切改动 3-5 天**（每改一次重置一次学习期）
2. 11-19/11-20 复检 PMax 恢复曲线；若仍 <10% 预算再一次性干预
3. 后续可选项：部分核心大词恢复 BROAD（理由：池子已被 PRESENCE 洗干净，同样的 BROAD 现在只匹配美国人，"大词无效"的前提已变）
4. 挂每日花费 <10% 预算自动告警（待用户确认）

## 数据口径备注
- 账户 7059800494（estry），币种 CNY、时区 Asia/Shanghai
- change_event 为权威记录；client_type=GOOGLE_ADS_API，email=bszanezeng@gmail.com（同一 OAuth 授权账号，无法从 API 区分具体工具）
- 历史背景：11-09~13 南亚低价点击井喷（BROAD+INTEREST 双宽松的产物），正是用户"大词无效"体感与本次收窄操作的动机来源

## API 坑（v26 REST）
- change_event 查询必须带 LIMIT ≤10000
- campaign_criterion.type（无下划线）；geo 字段路径 = campaign_criterion.location.geo_target_constant
- change_event.changed_fields 是字符串不是列表
