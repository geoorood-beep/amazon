# 老品广告 Agent 逻辑漏洞定位清单

> 审计对象：老品广告分析、决策、输出与执行链路  
> 审计日期：2026-07-24  
> 行号基准：`/Users/calvin/Desktop/广告agent/` 当前版本  
> 用途：供产品、运营和开发团队逐条确认、修正规则并编写回归测试

## 0. 审计边界与已确认前提

本清单只分析老品逻辑，并采用以下已确认业务前提：

1. 公司固定执行 `1 Campaign = 1 Ad Group`。
2. 因此，本清单不再把“广告组预算与 Amazon Campaign 预算层级不同”列为问题。
3. 但系统仍应保存 Campaign 与 Ad Group 的不可变 ID，并校验一对一关系，否则后台对象仍可能映射错误。
4. 默认库存充足，不把库存校验纳入日常决策或本次漏洞清单。
5. 人工只审批高影响动作批次，不要求逐条审批所有普通动作。

## 1. 严重度与问题类型

| 标记 | 含义 |
|---|---|
| `P0` | 会让同一输入得到相反或多个执行结果，或可能直接执行错误对象；应先修复 |
| `P1` | 会导致动作叠加、无法仲裁、无法验收或结果不可复现；应进入第一阶段开发 |
| `P2` | 边界、字段、来源或定义错误；应与主修复同步清理 |
| `明确矛盾` | 两条现有规则可被同一数据同时命中，且结果不同 |
| `覆盖空档` | 某些合法输入无法命中任何状态 |
| `约束缺失` | 规则有方向，但缺少优先级、上限、唯一对象或执行条件 |
| `不可验收` | 方案可以生成，但没有独立机制证明数据正确、逻辑自洽、动作可安全执行 |

## 2. 本次行号对应的源文件版本

源文档修改后行号会变化。开发修复时应以文件哈希和本清单中的规则原文摘要共同定位。

| 文档 | SHA-256 |
|---|---|
| `AGENTS.md` | `2fa189b5db8eb52904696f5c6e5b1341b23edc16b9a8a82a7a8957502d7adab2` |
| `old-product-promotion.md` | `9876818d3b52f22bdf89cbbf6af499a1281ee2fb26422673f524f09af1d8d411` |
| `category data thresholds.md` | `d3fe856ce5ce2183e155fb316d762629ad8ec351c50fda5fc3f4e83dee249b66` |
| `search-term-reinvestment.md` | `3984c0e34f1eabbeae43c8439c5f786567bd57ddd7ce2994a287558683e07023` |
| `promo-output-templates.md` | `4e6a0c4f7716be1948d8dfb5e7f42f6f56b2c493cfaa5226dcb9c4c5e2e0ffef` |

---

# A. P0：明确矛盾、覆盖空档与错误执行风险

## L-001 阈值四档不是互斥区间，同一个指标可同时命中多个档位

- **类型**：`P0 / 明确矛盾`
- **位置 A**：[`category data thresholds.md` 第 5 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:5>)规定列顺序为“优质｜正常｜警戒｜高风险”。
- **位置 B**：[`category data thresholds.md` 第 105–117 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:105>)和[第 125–155 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:125>)使用相互包含的条件。
- **受影响下游**：[`search-term-reinvestment.md` 第 118–119 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:118>)会按档位给 CVR、ACOS 不同分值。
- **具体问题**：
  - 10L `ACOS=55%` 同时满足警戒 `>=40%` 和高风险 `>=55%`。
  - 10L `CPA=$32` 同时满足警戒 `>=$25` 和高风险 `>=$32`。
  - 门垫 `CVR=3%` 同时满足警戒 `<5%` 和高风险 `<3.5%`。
  - 多数正常线的端点也与优质线或警戒线重叠，例如 `ACOS=30%` 同时满足 `<=30%` 与 `30%-40%`。
- **风险**：同一条数据可能得到 8 分或 0 分，也可能因判断顺序不同得到“警戒”或“高风险”。
- **必须修改**：将每项指标改成互斥、连续的上下界对象，例如：

```yaml
acos:
  quality: {min_exclusive: null, max_inclusive: 30}
  normal: {min_exclusive: 30, max_exclusive: 40}
  warning: {min_inclusive: 40, max_exclusive: 55}
  high_risk: {min_inclusive: 55, max_inclusive: null}
```

- **验收条件**：对每套阈值做边界值测试，任何合法数值必须且只能命中一个档位。

## L-002 四套地毯 CVR 阈值存在明确空档

- **类型**：`P0 / 覆盖空档`
- **位置**：
  - 门垫：[`category data thresholds.md` 第 125 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:125>)
  - 长条：[`category data thresholds.md` 第 135 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:135>)
  - 小区域：[`category data thresholds.md` 第 143 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:143>)
  - 大区域：[`category data thresholds.md` 第 151 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:151>)
- **具体空档**：
  - 门垫：`6.5% < CVR < 7.5%`
  - 长条：`7.5% < CVR < 8%`
  - 小区域：`5% < CVR < 5.5%`
  - 大区域：`4.5% < CVR < 5%`
- **风险**：这些数值无法进入优质、正常、警戒或高风险中的任何一档，后续评分和动作为空。
- **必须修改**：先由业务确认空档应归入“正常”还是“优质”；代码层禁止用默认档位静默补齐。
- **验收条件**：从 `0%` 到合理上限的连续值域不存在空档。

## L-003 “订单少于 2 单只能观察”与“少于 2 单达到停止线可强动作”直接冲突

- **类型**：`P0 / 明确矛盾`
- **位置 A**：[`category data thresholds.md` 第 5 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:5>)及[第 43 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:43>)规定 `O<2` 只能观察。
- **位置 B**：同文档[第 108–117 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:108>)及[第 128–155 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:128>)又把 `O<2` 的点击/花费定义为警戒、高风险或停止线。
- **位置 C**：[`old-product-promotion.md` 第 103 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:103>)规定“无订单且花费达到停止线”可降价、否定、降预算或暂停；但[第 106 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:106>)又规定订单样本不足只能观察。
- **位置 D**：[`old-product-promotion.md` 第 253、255 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:253>)分别要求达到停止线后可降 Bid/否定，以及样本不足只观察。
- **风险**：同一无单对象可以同时生成“保持观察”和“否定/降 Bid/暂停”。
- **必须修改**：二选一并写入全局优先级：
  1. 若坚持 `O<2` 一律观察，则将点击/花费线改名为“无单风险观察线”，不赋予自动停止权。
  2. 若允许停止例外，则明确 `O=0 + 归因成熟 + 达到品类停止线 + 对象映射完成` 是一般观察规则的唯一例外；高影响停止动作进入聚合审批。
- **验收条件**：相同对象在同一轮只能输出一个最终状态，不得同时出现“观察”和强收缩动作。

## L-004 固定“15 点击 0 单默认精否”绕过品类停止线和有限数据权限

- **类型**：`P0 / 明确矛盾`
- **位置 A**：[`search-term-reinvestment.md` 第 130 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:130>)规定低分词只有达到“类目停止线”才可成为 Negative Exact 候选。
- **位置 B**：同文档[第 191 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:191>)又规定单搜索词 `点击>=15 且订单=0` 默认 Negative Exact。
- **位置 C**：品类点击停止线分别为 25、30、35、40、50、55 等，[`category data thresholds.md` 第 108–117、128–155 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:108>)。
- **位置 D**：[`AGENTS.md` 第 74–78 行](</Users/calvin/Desktop/广告agent/AGENTS.md:74>)和[`old-product-promotion.md` 第 53–55 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:53>)规定有限数据模式只能输出否词候选，不能直接实施。
- **风险**：15 点击规则可在尚未达到门垫 40 点击、大区域 55 点击等停止线时直接否词，也可能越过“待投放对象映射”限制。
- **必须修改**：删除第 191 行的独立执行权，统一改为：

```text
完整报表模式
AND 搜索词与 Target 映射完成
AND 归因窗口成熟
AND 达到当前品类停止线
=> 可生成 Negative Exact 动作
否则 => 仅生成候选
```

- **验收条件**：任何否词动作均能回溯到品类停止线、数据模式和唯一投放对象。

## L-005 历史词根优化分 `65–69` 同时对应两种动作

- **类型**：`P0 / 明确矛盾`
- **位置 A**：[`search-term-reinvestment.md` 第 128 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:128>)规定 `65–84` 为达标保留/Phrase 复投候选。
- **位置 B**：同文档[第 129 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:129>)规定 `50–69` 为控制观察/Broad 低预算候选。
- **风险**：65、66、67、68、69 分均可得到 Phrase 复投和 Broad 低预算观察两套结论。
- **必须修改**：将第 129 行改为 `50–64`；同时增加程序断言“每个分数只能命中一个动作等级”。
- **验收条件**：0–100 每个整数恰好命中一个等级。

## L-006 用户目标 ACOS 与品类高风险线没有优先级，可同时判为“高效”和“低效”

- **类型**：`P0 / 明确矛盾`
- **位置 A**：[`old-product-promotion.md` 第 100 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:100>)按 `ACOS<=用户目标` 判定高效且达量。
- **位置 B**：同文档[第 103 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:103>)按 `ACOS>品类高风险线` 判定低效无量。
- **阈值示例**：大区域 Rug 高风险线为 `ACOS>=50%`，[`category data thresholds.md` 第 152 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:152>)。
- **触发例**：用户目标 ACOS 为 60%，实际 ACOS 为 55%，订单达标且出单词花费占比大于 25%。该对象同时满足“高效且达量”和“品类高风险”。
- **风险**：同一对象可同时得到“保持/增加预算”和“降预算/暂停”。
- **必须修改**：增加显式优先级与冲突状态：

```text
若 用户目标线宽于品类高风险线 且实际值落在两者之间
=> 状态 = 目标与品类风险冲突
=> 禁止自动执行，进入高影响批次审批
```

- **验收条件**：所有整体状态互斥；目标与风险线发生倒挂时不得自动选择任一动作。

## L-007 整体效果四状态没有覆盖全部条件组合

- **类型**：`P0 / 覆盖空档`
- **位置**：[`old-product-promotion.md` 第 98–106 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:98>)。
- **未覆盖示例**：
  1. `ACOS<=目标`、订单达标，但出单词花费占比为 20%：不满足第 100 行，也不满足其他状态。
  2. 订单未达标，且 `目标ACOS < 实际ACOS <= 正常线`：不属于高效量少，也不属于“有量超标”。
  3. 订单已达标，但 ACOS 位于正常线与高风险线之间：没有状态。
  4. ACOS 超高风险线但订单量充足时，第 103 行仍命名为“低效无量”，名称与事实不一致。
- **风险**：系统可能返回空状态、落入实现者自定义兜底，或错误套用“低效无量”动作。
- **必须修改**：把条件写成完整真值表，至少补充：
  - `效率达标但结构风险`
  - `未达量且成本超目标`
  - `有量且高风险`
  - `数据冲突/不可判定`
- **验收条件**：对效率、订单完成、花费结构、数据充分度的所有组合做覆盖测试，恰好命中一个状态。

## L-008 “高效但量少要查广告位”与“整体达标不分析广告位”冲突

- **类型**：`P0 / 明确矛盾`
- **位置 A**：[`old-product-promotion.md` 第 101 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:101>)要求高效但量少时检查广告位。
- **位置 B**：同文档[第 183–186 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:183>)规定整体达到标准值时不分析广告位。
- **问题**：“整体达到标准值”未说明是只看 ACOS，还是同时要求订单达量。高效但量少在 ACOS 意义上已达标，在订单意义上未达标。
- **风险**：相同数据可能因实现者对“整体达标”的理解不同而跳过或进入广告位诊断。
- **必须修改**：删除自然语言门槛，改为状态枚举：

```text
overall_state in {高效量少, 有量超标, 有量高风险, 低效无量}
=> 允许进入广告位诊断
```

- **验收条件**：每个整体状态是否进入广告位模块由固定布尔表决定。

## L-009 不同趋势指标可同时触发“恢复”和“恶化”

- **类型**：`P0 / 明确矛盾`
- **位置 A**：[`old-product-promotion.md` 第 284 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:284>)规定 ACOS、CPA、CVR 任一指标满足即可标记趋势。
- **位置 B**：同文档[第 288–304 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:288>)把趋势状态映射到不同动作。
- **触发例**：近 3 天 ACOS 改善 15%，但 CVR 恶化 20%。按“任一指标”规则，同一对象既可标记“恢复”，也可标记“近期转差/连续恶化”。
- **风险**：同时生成恢复 Bid/预算和降 Bid/收预算动作。
- **必须修改**：增加 `混合信号` 状态，并指定主指标或一致性条件。建议要求“主指标 + 至少一个辅助指标同向”才允许触发动作；混合信号只观察。
- **验收条件**：一个对象、一个观察时点只能有一个趋势状态。

## L-010 “完整模式必须可执行”，但输出字段不足以唯一定位和安全执行

- **类型**：`P0 / 错误执行风险`
- **位置 A**：[`promo-output-templates.md` 第 3 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:3>)要求报表齐全时必须可执行。
- **位置 B**：同文档[第 53–62 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:53>)的老广告表只有广告组名称、ASIN、调整方向和判断依据。
- **位置 C**：同文档[第 68–78 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:68>)的新广告表也缺少 Campaign 对象、动作 ID、当前值与目标值。
- **缺失字段**：
  - `Campaign_ID`
  - `Ad_Group_ID`
  - `Target_ID / Keyword_ID`
  - `Action_ID`
  - `action_level`
  - `current_value`
  - `proposed_value`
  - `unit`
  - `precondition`
  - `rollback_value`
- **风险**：名称重复、后台状态变化或重复运行时，执行器可能改错对象或重复执行同一动作。
- **必须修改**：完整模式必须输出不可变 ID 和 `当前值→目标值`；只有方向或百分比的行不得进入执行表。
- **验收条件**：每条执行动作能唯一定位一个后台对象，并可在执行前验证当前值、执行后恢复原值。

## L-011 最终方案只有“自我解释”，没有独立 PASS/WARN/BLOCK 验收门

- **类型**：`P0 / 不可验收`
- **位置 A**：[`AGENTS.md` 第 83–86 行](</Users/calvin/Desktop/广告agent/AGENTS.md:83>)只要求说明观察周期、指标、规则和原因。
- **位置 B**：[`old-product-promotion.md` 第 336–354 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:336>)要求在方案下方写“判断依据与设计逻辑”。
- **位置 C**：[`promo-output-templates.md` 第 164–189 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:164>)同样只要求自然语言说明。
- **位置 D**：[`old-product-promotion.md` 第 332 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:332>)仅规定部分动作人工审核，没有交付前系统验收。
- **具体问题**：生成动作的同一套逻辑同时负责解释动作，不构成独立校验；没有检查：
  - 输入汇总与明细是否对平
  - 阈值是否唯一命中
  - 同一对象是否有相反动作
  - Campaign/Ad Group/Target 是否唯一映射
  - 执行字段是否齐全
  - 是否超出批次影响上限
- **风险**：方案可以“解释得通”，但数据、映射或执行值仍然错误。
- **必须修改**：增加独立验收器，生成器输出候选动作后再运行：

```text
数据对账
→ 阈值与状态唯一性
→ 对象映射
→ 动作冲突/叠加
→ 执行字段完整性
→ 风险与审批分级
→ PASS / WARN / BLOCK
```

`BLOCK` 不得输出可执行动作，只能输出待修复原因；`WARN` 只能输出候选或进入聚合审批。
- **验收条件**：人为构造金额不平、双状态、双动作、缺 ID、后台值已变化等异常时，验收器必须阻断。

---

# B. P1：动作冲突、因果归因、执行和验证约束缺失

## L-012 高效广告的“预算受限”判断被小时模块入口规则切断

- **类型**：`P1 / 约束缺失`
- **位置 A**：[`old-product-promotion.md` 第 100 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:100>)允许高效达量且预算受限时增加预算。
- **位置 B**：同文档[第 110–117 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:110>)规定整体效果好时不判断小时花费节奏。
- **问题**：预算是否提前耗尽通常需要小时预算/花费数据，但高效广告被禁止进入该模块。
- **风险**：第 100 行的“预算受限”无法稳定取得证据，只能靠实现者猜测。
- **修改建议**：把“预算是否受限”设为独立只读检查。整体好时可以识别“预算耗尽时间、错失曝光”，但不做时段好坏判断。

## L-013 固定 `06:00–18:00` 理想花费曲线缺少站点、时区、类目和数据来源

- **类型**：`P1 / 约束缺失`
- **位置 A**：[`old-product-promotion.md` 第 126–152 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:126>)把固定曲线作为自动监控基准。
- **位置 B**：同文档[第 33 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:33>)只要求小时预算/花费报告，没有规定站点时区、数据时区或历史校准样本。
- **风险**：US、EU 等站点、不同类目和不同受众时段可能完全不同；统一曲线会系统性误判“过快/过慢”。
- **修改建议**：未维护 `marketplace + timezone + category + effective_period` 曲线时，只输出实际耗尽时间，不判断好坏；有足够历史数据后再按账户/类目校准。

## L-014 Bid 规则可对同一 Target 同时要求提价和降价

- **类型**：`P1 / 动作冲突`
- **位置**：[`old-product-promotion.md` 第 169–175 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:169>)。
- **触发例**：Target 曝光少、历史有转化，可命中第 169 行“提高 Bid”；同一 Target 当前 CPA 超标，又可命中第 173 行“降低 Bid”。
- **问题**：规则没有主次指标、优先级、冲突状态或动作仲裁。
- **修改建议**：先形成 `Target 状态`，再映射唯一动作；成本不达标时默认禁止提 Bid，除非明确进入小预算探索状态。

## L-015 “小幅”“单次上限”“大幅”均未量化

- **类型**：`P1 / 约束缺失`
- **位置**：
  - 提 Bid 受单次上限约束：[`old-product-promotion.md` 第 169 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:169>)
  - 小幅拓量/降 Bid：同文档[第 172–173 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:172>)
  - 大幅降预算需审批：同文档[第 332 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:332>)
- **问题**：全部文档均未定义比例、金额或动态计算公式。
- **风险**：不同开发者可把“小幅”实现成 5%、20% 或 50%，审批边界也无法判断。
- **修改建议**：配置化定义 `single_action_cap`、`batch_effect_cap`、`large_change_threshold`，并按对象层级和动作类型区分。

## L-016 用基础 Bid 放大单一优质广告位，会同步放大其他差广告位

- **类型**：`P1 / 因果冲突`
- **位置 A**：[`old-product-promotion.md` 第 209、219–220 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:209>)允许为某一位置提高基础 Bid。
- **位置 B**：同文档[第 227 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:227>)明确基础 Bid 会同时影响多个广告位。
- **风险**：为了获取更多高效 TOS 流量提高基础 Bid，同时也可能放大低效 PP/ROS。
- **修改建议**：单位置目标默认只调整对应位置控制项；只有所有位置都缺量且联合有效竞价校验通过时，才允许调整基础 Bid。

## L-017 “想要更多 PP 就降低基础 Bid”会同时削弱 PP 的绝对获取能力

- **类型**：`P1 / 逻辑表述错误`
- **位置 A**：[`old-product-promotion.md` 第 221、223 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:221>)要求降低基础 Bid、把 TOS/ROS 溢价降为 0，以获得或保留 PP。
- **位置 B**：同文档[第 227 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:227>)说明基础 Bid 影响多个广告位。
- **问题**：该动作可能提高 PP 的相对花费占比，但不会保证获得更多 PP；降低基础 Bid 也会降低 PP 的绝对竞价。
- **修改建议**：把目标改成“提高 PP 相对占比”；若 TOS/ROS 已为 0 仍无法隔离，则输出“需要结构隔离”，不得声称降低基础 Bid 能保留 PP 获取能力。

## L-018 连续恶化可同时执行五类收缩动作，没有组合影响上限

- **类型**：`P1 / 动作叠加`
- **位置 A**：[`old-product-promotion.md` 第 302 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:302>)同时允许降 Bid、降溢价、否词、收预算、暂停。
- **位置 B**：同文档[第 327–332 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:327>)只有执行顺序，没有同对象主动作、组合动作或累计影响约束。
- **风险**：Target 降 Bid、Campaign 降预算、广告位降溢价并批量否词后，实际流量收缩远大于任何单项动作。
- **修改建议**：同一对象每轮只允许一个主收缩动作；确需组合时，作为一个 `Action_Package` 计算累计有效竞价、预算和流量影响，并受批次上限约束。

## L-019 使用嵌套的 3/7/14/30 天窗口证明“连续恶化”，统计口径不独立

- **类型**：`P1 / 统计逻辑问题`
- **位置**：[`old-product-promotion.md` 第 270–294 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:270>)。
- **问题**：最近 3 天同时包含在最近 7 天和 14 天中，不能把三个滚动窗口当成三个独立阶段。
- **风险**：最近 3 天的异常会同时影响 7 天、14 天数据，制造“连续恶化/恢复”的表象。
- **修改建议**：方向判断改用不重叠窗口 `D0–3、D4–7、D8–14、D15–30`；滚动窗口只用于描述当前水平。

## L-020 关闭表现差的匹配类型前，没有强制迁移其中的优质搜索词

- **类型**：`P1 / 执行顺序缺失`
- **位置 A**：[`old-product-promotion.md` 第 308 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:308>)规定效果差的类型优先关闭。
- **位置 B**：[`search-term-reinvestment.md` 第 74–82 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:74>)允许把已验证搜索词迁移到 Phrase/Broad/Exact。
- **风险**：Broad 整体表现差，但内部仍可能有稳定成交长尾词；直接关闭会同时丢失赢家流量。
- **修改建议**：关闭前强制执行“提取赢家查询→建立承接对象→确认启用→再关闭剩余流量”的迁移检查。

## L-021 “效果好的类型不拆分”过于绝对，与结构修复目标冲突

- **类型**：`P1 / 规则过度约束`
- **位置 A**：[`old-product-promotion.md` 第 309 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:309>)规定效果好的类型不提出拆分重建。
- **位置 B**：同文档[第 311、331 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:311>)又要求处理预算分散、无法归因和内部竞争。
- **触发例**：Broad 整体达标，但一个大词占用 80% 预算，导致其他已验证词拿不到流量。
- **修改建议**：改为“效果好默认不拆”；存在明确预算挤占、不可归因或目标不同证据时，允许保留原组基线并做小规模隔离。

## L-022 Phrase + Broad 并行架构可能在下一轮被判为内部竞争

- **类型**：`P1 / 跨文档口径冲突`
- **位置 A**：[`search-term-reinvestment.md` 第 79–81 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:79>)要求 Phrase 与 Broad 分组并行。
- **位置 B**：[`old-product-promotion.md` 第 310 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:310>)将同一关键词在多个相同目的广告组重复投放判为内部竞争。
- **问题**：系统没有定义 Phrase 承接和 Broad 拓词是否属于“相同目的”。
- **修改建议**：增加 `traffic_role / overlap_intent` 字段；只有产品、投放对象、匹配方式、目标和流量角色均相同时才判重复。

## L-023 多词根归属只禁止横向求和，没有禁止生成重复或相反动作

- **类型**：`P1 / 执行去重缺失`
- **位置 A**：[`AGENTS.md` 第 102–104 行](</Users/calvin/Desktop/广告agent/AGENTS.md:102>)允许同一搜索词进入多个 ABA 词根，并禁止横向求和。
- **位置 B**：[`search-term-reinvestment.md` 第 65–68、121 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:65>)允许多词根分别聚合评分。
- **位置 C**：[`old-product-promotion.md` 第 250–253 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:250>)会据词根结果生成复投、否词或加预算动作。
- **风险**：同一个搜索词可能因两个词根被重复建组、重复分配预算，甚至一处放量、一处否定。
- **修改建议**：动作层增加唯一去重键：

```text
ASIN + Search_Term + Ad_Product + Match_Type + Traffic_Role
```

多词根只保留证据归属，最终必须仲裁为一个主动作。

## L-024 “战略角色”可以绕过 Exact 的数据验证门槛

- **类型**：`P1 / 权限绕过`
- **位置 A**：[`search-term-reinvestment.md` 第 57–59 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:57>)规定 Exact 只能使用词级证据。
- **位置 B**：同文档[第 82 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:82>)又规定承担排名/收割/防守角色时可以单独拉 Exact。
- **问题**：第 82 行使用“或”，战略标签可完全绕过样本门槛。
- **修改建议**：拆成“绩效 Exact”和“战略 Exact”。战略 Exact 必须单独小预算、独立标识并进入高影响批次审批，不得伪装成绩效验证通过。

## L-025 词根达到拓量条件后，最终复制哪个具体对象没有定义

- **类型**：`P1 / 执行对象不唯一`
- **位置 A**：[`search-term-reinvestment.md` 第 161–167 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:161>)允许搜索词、投放词或词根聚合进入拓量池。
- **位置 B**：[`old-product-promotion.md` 第 259–266 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:259>)允许从 SP 复制到其他广告产品。
- **问题**：词根可能由多个弱搜索词聚合而成，但规则未说明最终复制完整搜索词、原 Target 还是抽象词根。
- **风险**：聚合层表现会被错误下放到一个从未单独验证的具体词。
- **修改建议**：增加 `expansion_execution_object`。默认只允许复制已验证完整搜索词或真实投放对象；词根须通过订单集中度门槛后才可下放。

## L-026 A 档可同时新增 SPV、SB、SBV，但没有渠道仲裁和批次总预算

- **类型**：`P1 / 动作叠加`
- **位置 A**：[`search-term-reinvestment.md` 第 173 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:173>)写“新增 SPV / SB / SBV 复制验证”。
- **位置 B**：[`promo-output-templates.md` 第 88–93 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:88>)允许同词拆成多行同时新增多个广告产品。
- **位置 C**：[`old-product-promotion.md` 第 268、331 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:268>)要求每个新增广告按 CPA 预算设置，但没有批次总预算限制。
- **风险**：同一个词一次开三个新广告产品，预算和流量影响成倍扩大，验证结果互相污染。
- **修改建议**：默认首轮只验证一个新广告产品；多渠道同时测试时必须共享 `Expansion_Batch_ID`、批次总预算、渠道优先级、是否互斥和独立成功标准。

## L-027 “稳定”“没有明显转差”“跑出稳定结果”均无统一定义

- **类型**：`P1 / 定义缺失`
- **位置**：
  - “没有明显转差”：[`search-term-reinvestment.md` 第 166 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:166>)
  - “近 3 天稳定”：同文档[第 173 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:173>)
  - “跑出稳定结果”：同文档[第 185 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:185>)
  - 老品规则也使用“表现稳定”：[`old-product-promotion.md` 第 259 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:259>)
- **风险**：相同数据可因解释不同进入或不进入拓量，第二轮预算放大也没有确定门槛。
- **修改建议**：统一成可计算的 `stability_status`，明确观察期、最低点击/订单、CPA/ACOS/CVR边界和允许波动范围。

## L-028 同一套 SKU/尺寸阈值被直接用于 Campaign、广告位、商品和趋势，适用粒度不明确

- **类型**：`P1 / 粒度错配`
- **位置 A**：[`old-product-promotion.md` 第 73–77 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:73>)要求整体、广告位、广告商品和趋势调用同一阈值文件。
- **位置 B**：[`category data thresholds.md` 第 42 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:42>)只要求映射到尺寸/ASIN/SKU，没有给出各阈值适用的数据层级。
- **位置 C**：[`old-product-promotion.md` 第 317–325 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:317>)明确存在产品、Campaign、广告组、Target、搜索词、广告位和时间等不同层级。
- **风险**：SKU 阈值可能被直接套到多 Target 汇总、广告位汇总或混合尺寸 Campaign 上。
- **修改建议**：每套阈值增加 `applicable_grain`；当前阈值先限定在 SKU/尺寸层。上层聚合必须先汇总原始分子分母，再按明确规则标准化。

## L-029 广告位和广告商品汇总没有控制 Target/匹配方式差异，可能把流量问题误判成位置或商品问题

- **类型**：`P1 / 归因混杂`
- **位置 A**：[`old-product-promotion.md` 第 193–213 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:193>)按广告位汇总判断。
- **位置 B**：同文档[第 229–238 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:229>)按商品表现决定暂停、换品、拆分。
- **位置 C**：同文档[第 317–322 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:317>)把 Target、商品和广告位定义为不同层级。
- **触发例**：
  - Exact 在 TOS 高效、Broad 在 TOS 低效，汇总 TOS 后提高溢价会同时放大 Broad。
  - SKU-A 主要承接 Broad、SKU-B 主要承接 Exact，直接比较商品 CPA 会把流量结构差异归因于商品。
- **修改建议**：高影响动作需要“Target×广告位”或可比流量结构证据；无法同口径比较时，只输出“结构混杂，需隔离验证”。

## L-030 标准最低日预算公式中的 `N` 没有时间单位，且预算金额被误当成数据充分度

- **类型**：`P1 / 量纲与因果错误`
- **位置 A**：[`category data thresholds.md` 第 47–57 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:47>)规定 `日预算=CPA正常线上限×N`，但只称 N 为“目标订单数”。
- **位置 B**：[`promo-output-templates.md` 第 132–153 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:132>)重复相同规则，并把达到该预算称为“可判断出单”。
- **位置 C**：阈值规则又要求至少 `O>=2` 才能判断，[`category data thresholds.md` 第 5、43 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:5>)。
- **问题**：
  - 若 N 是测试期总订单，公式量纲错误。
  - 即使预算达到一个 CPA 上限，也不代表实际花费、点击和订单样本已经充分。
- **修改建议**：
  - 明确 `N=单 Campaign 目标广告订单/日`。
  - 将名称改为“计划测试日预算”。
  - 数据充分度只依据实际成熟点击、花费、订单和观察周期，不能由预算配置值推断。

## L-031 多个新增 Campaign 没有总预算约束

- **类型**：`P1 / 组合约束缺失`
- **位置 A**：[`category data thresholds.md` 第 47–76 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:47>)只逐个计算标准最低预算。
- **位置 B**：[`old-product-promotion.md` 第 331 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:331>)允许同时新增、重建和跨广告产品拓量。
- **问题**：即使遵守 `1 Campaign = 1 Ad Group`，同时创建多个 Campaign 时仍可能把每个 CPA 预算直接相加，超过用户总预算。
- **修改建议**：增加批次约束：

```text
Σ新增或调增后的 Campaign 日预算变化
<= 本批次可用总预算
```

超限时按优先级分配，不得逐 Campaign 独立通过。

## L-032 人工审批只覆盖少数动作，也没有按影响汇总成批次

- **类型**：`P1 / 审批边界缺失`
- **位置 A**：[`old-product-promotion.md` 第 332 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:332>)只明确暂停、大幅降预算、超配置上限需人工审核。
- **位置 B**：同文档[第 302、331 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:302>)还可能产生批量否词、Bid/溢价变化、重建和跨广告产品拓量。
- **风险**：100 条小动作逐条看似低风险，但汇总后可能影响大部分广告花费；反之，人工逐条审批又不可执行。
- **修改建议**：按影响批次分级，而不是按单条动作名称：
  - 自动执行：单条和批次影响均低于上限。
  - 登记后执行：中影响，可抽样复核。
  - 聚合审批：预计影响花费/销售达到阈值、批量否词、重建、策略切换或多渠道拓量。
  - 阻断：对象不唯一、动作冲突、数据未通过验收。

## L-033 跨广告产品的关键字段允许藏在“判断依据”自然语言中

- **类型**：`P1 / 不可机器校验`
- **位置**：[`promo-output-templates.md` 第 80–91 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:80>)允许关键字段“补充字段或写在判断依据中”。
- **风险**：来源对象、指标、素材、优先级和风险无法自动筛选、审批、聚合或验收。
- **修改建议**：删除“或写在判断依据中”；所有执行与风险字段改为结构化必填列，自然语言只做人读摘要。

## L-034 完整模式要求可执行，但模板又默认只输出 1–2 张核心表

- **类型**：`P1 / 输出要求冲突`
- **位置 A**：[`promo-output-templates.md` 第 3 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:3>)要求完整模式必须可执行。
- **位置 B**：同文档[第 157 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:157>)规定优先 1–2 张核心表，除非用户要求完整后台动作清单。
- **风险**：即使数据完整，系统仍可能只输出策略摘要，而没有机器可执行动作表。
- **修改建议**：完整模式固定包含机器可执行动作表；“1–2 张”只限制用户展示摘要，不限制后台执行数据集。

## L-035 缺少幂等、执行前状态和数据快照机制

- **类型**：`P1 / 重复与过期执行风险`
- **位置 A**：[`promo-output-templates.md` 第 53–78 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:53>)没有 Action_ID、当前值、生成时间、有效期和前置条件。
- **位置 B**：[`old-product-promotion.md` 第 25 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:25>)只要求当前设置表；趋势规则使用多日数据，[第 270–294 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:270>)，但没有设置变更历史。
- **风险**：
  - 同一方案重复运行会再次加/降相同百分比。
  - 生成后后台已被人工修改，旧动作仍可能覆盖新值。
  - 历史表现跨越了一次 Bid/预算变更，却被当成同一策略阶段。
- **修改建议**：每个动作包含 `Action_ID、input_snapshot_id、generated_at、expires_at、expected_current_value`；执行前不匹配则 BLOCK。趋势应按设置变更点切段。

## L-036 公司“1 Campaign = 1 Ad Group”业务约束没有写入规则和输出校验

- **类型**：`P1 / 业务不变量缺失`
- **位置 A**：[`old-product-promotion.md` 第 25 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:25>)要求 Campaign/Ad Group 设置表，但未声明一对一。
- **位置 B**：[`promo-output-templates.md` 第 55 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:55>)和[第 70 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:70>)只把广告组名称设为标准字段。
- **说明**：这里不是“广告组预算层级错误”；该问题已按业务前提排除。真正漏洞是系统没有把一对一关系编码成硬约束。
- **风险**：导入异常数据、历史遗留 Campaign 或错误映射时，系统不会阻断；仅凭广告组名称也不能唯一定位 Campaign。
- **修改建议**：导入后断言每个 Campaign 恰好映射一个 Ad Group；不满足时 `BLOCK + 数据异常`。执行表同时保存两个 ID。

## L-037 跨报表只要求“互相校验”，没有定义对账口径和唯一事实源

- **类型**：`P1 / 数据正确性缺口`
- **位置 A**：[`old-product-promotion.md` 第 20–25 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:20>)要求多个不同粒度报表，第 21 行仅说汇总与每日明细互相校验。
- **位置 B**：同文档[第 87 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:87>)要求检查日期、归因、币种、样本和映射。
- **位置 C**：同文档[第 317–325 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:317>)定义多个聚合层级，但没有定义允许误差、归因窗口、去重键或哪个报表是各指标的事实源。
- **风险**：搜索词、Target、Campaign、广告位和商品报表合计不一致时，系统可任意选一份继续决策。
- **修改建议**：建立 `reconciliation_spec`：
  - 每项指标的 canonical source
  - 日期与归因窗口
  - 币种与时区
  - 去重键
  - 允许误差
  - 超差后的 WARN/BLOCK 规则

---

# C. P2：应立即同步修正的边界、来源和字段小错误

## L-038 长条阈值从 2x5 直接扩展到全部长条尺寸，没有验证依据

- **类型**：`P2 / 适用范围外推`
- **位置 A**：[`category data thresholds.md` 第 38 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:38>)说明来源仍是原 2x5。
- **位置 B**：同文档[第 133 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:133>)将其应用到全部长条产品。
- **问题**：2x4 到 3x20/4x12 的价格、流量和转化可能显著不同，文档没有外推样本或校准规则。
- **修复**：未验证尺寸先标记“借用 2x5 参考阈值，仅观察”；或按价格/面积带重新校准。

## L-039 `57.5 平方英尺` 区域分界只是两个锚点的算术中点

- **类型**：`P2 / 临时经验值被当成强规则`
- **位置**：[`category data thresholds.md` 第 40 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:40>)。
- **问题**：文档明确 57.5 来自 5x7 与 8x10 面积中点，不是广告表现数据的经验分界，却被用于路由全部区域尺寸。
- **修复**：标记为临时路由且只允许观察，或用历史 CPA/CVR/ACOS 分布重新确定分界。

## L-040 尺寸映射含 `20x30`、`30x48`，但映射表本身未携带单位

- **类型**：`P2 / 字段歧义`
- **位置 A**：[`category data thresholds.md` 第 15–18 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:15>)按数字进行尺寸标准化。
- **位置 B**：同文档[第 27 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:27>)把 `20x30`、`30x48` 列为区域。
- **位置 C**：同文档[第 40 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:40>)又要求英寸先换算。
- **问题**：若 `30x48` 是英寸，则换算后为 `2.5x4ft`，按第 18 行应归长条；若是英尺则归区域。
- **修复**：尺寸必须携带单位，统一换算为英尺后再执行形状、短边和面积规则。

## L-041 地毯阈值来源使用不可迁移的 Windows 绝对路径，且缺少版本元数据

- **类型**：`P2 / 来源不可复核`
- **位置 A**：[`AGENTS.md` 第 35 行](</Users/calvin/Desktop/广告agent/AGENTS.md:35>)规定项目路径应可迁移，不依赖原电脑绝对路径。
- **位置 B**：[`category data thresholds.md` 第 121 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:121>)却使用 `D:\Downloads\数据标准.docx`。
- **问题**：来源没有 marketplace、币种、统计周期、样本量、版本、文件哈希和录入复核记录。
- **修复**：把源文件纳入项目 `reference/`，记录 `marketplace、currency、source_period、sample_n、version、hash、录入复核人`；缺失时阈值只作人工参考。

## L-042 ABA 尺寸映射只有文件月份，没有生效与失效版本

- **类型**：`P2 / 版本控制缺失`
- **位置**：[`category data thresholds.md` 第 11 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:11>)。
- **问题**：来源文件名带 `202605`，但没有 `effective_from、expires_at、source_hash`，无法确认 ABA 更新后是否已重新汇总。
- **修复**：保存映射生成时间、来源哈希、生效期和失效期；源文件变化时强制重新生成。

## L-043 “数据置信度：高/中/低”没有评分标准或阻断作用

- **类型**：`P2 / 定义缺失`
- **位置**：[`promo-output-templates.md` 第 35 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:35>)。
- **风险**：相同的报表缺失情况可以被任意标高、中或低，低置信度也没有阻止高风险动作。
- **修复**：用报表覆盖率、对象映射率、观察期、样本门槛和对账状态定义置信度；低置信度不得生成高影响执行动作。

## L-044 “订单完成率、目标完成率、目标线”没有公式、周期和分母

- **类型**：`P2 / 指标定义缺失`
- **位置 A**：[`old-product-promotion.md` 第 88 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:88>)把订单完成率和目标完成率列为核心指标。
- **位置 B**：同文档[第 100–102 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:100>)用订单完成率决定整体状态。
- **位置 C**：[`promo-output-templates.md` 第 31–35 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:31>)只要求“当前订单目标”，没有日/周/月、广告订单/总订单口径。
- **修复**：固定定义分子、分母、周期、时区及广告归因口径；未提供目标时不得调用相关状态。

## L-045 广告商品诊断要求使用 CTR，但阈值文件明确缺少 CTR 标准

- **类型**：`P2 / 指标无判定标准`
- **位置 A**：[`old-product-promotion.md` 第 92、231 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:92>)要求商品层看 CTR。
- **位置 B**：[`category data thresholds.md` 第 101 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:101>)仅说明喂水器 CTR 标准未提供；地毯也没有 CTR 阈值。
- **风险**：实现者可能自行编造“CTR 好/差”标准，或不同品类使用同一标准。
- **修复**：无 CTR 阈值时只展示原值，不参与强动作；需要时按品类、广告类型和广告位单独维护。

## L-046 5L 花费高风险线使用 `S>$30`，与其他停止线的 `>=` 写法不一致

- **类型**：`P2 / 边界操作符不一致`
- **位置**：[`category data thresholds.md` 第 117 行](</Users/calvin/Desktop/广告agent/category data thresholds.md:117>)。
- **问题**：5L 为 `S>=$28` 警戒、`S>$30` 高风险；恰好 `$30` 不进入高风险。其他同类规则普遍使用 `>=`。
- **修复**：由业务确认 `$30` 是否应进入高风险；统一边界操作符并加入 `$29.99/$30/$30.01` 回归测试。

## L-047 预算用途在规则中有多个枚举，输出模板却只有一个“预算”字段

- **类型**：`P2 / 字段缺失`
- **位置 A**：[`AGENTS.md` 第 89 行](</Users/calvin/Desktop/广告agent/AGENTS.md:89>)区分标准最低预算、观察预算、拓词预算。
- **位置 B**：[`promo-output-templates.md` 第 73 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:73>)只要求“预算”。
- **位置 C**：同文档[第 152–153 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:152>)又依赖预算类型判断能否强判。
- **风险**：只输出 `$13` 时，无法知道它是标准、观察、拓词还是复制验证预算。
- **修复**：增加结构化字段 `budget_amount、currency、budget_type、calculation_basis、target_orders_per_day`。

## L-048 常规机会分对 CVR 重复计分，但没有说明为什么要给双重权重

- **类型**：`P2 / 权重重复`
- **位置 A**：[`search-term-reinvestment.md` 第 89 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:89>)在转化验证中给 CVR 12 分。
- **位置 B**：同文档[第 90 行](</Users/calvin/Desktop/广告agent/search-term-reinvestment.md:90>)又在效率机会中给 CVR 8 分。
- **问题**：CVR 共占 20 分，同时订单、CVR、ACOS 本身存在相关性；文档未说明双重权重是有意设计还是重复录入。
- **修复**：若为有意设计，写明业务理由和校准样本；否则去重并重新归一化 100 分。

## L-049 来源标签能说明“来自哪类数据”，但不能复现当时实际使用的数据与规则版本

- **类型**：`P2 / 可复现性缺失`
- **位置 A**：[`AGENTS.md` 第 85–86 行](</Users/calvin/Desktop/广告agent/AGENTS.md:85>)要求来源标签。
- **位置 B**：[`old-product-promotion.md` 第 344–352 行](</Users/calvin/Desktop/广告agent/old-product-promotion.md:344>)和[`promo-output-templates.md` 第 176–185 行](</Users/calvin/Desktop/广告agent/promo-output-templates.md:176>)列出标签种类。
- **问题**：标签没有记录报表文件哈希、导入时间、规则版本、阈值版本和生成时间。
- **修复**：每次完整方案保存 `rule_version、threshold_version、input_file_hashes、snapshot_id、generated_at`。

---

# D. 建议开发团队按此顺序处理

## 第一批：修完才能允许自动生成可执行动作

1. `L-001`、`L-002`：阈值改成连续且互斥。
2. `L-003`、`L-004`：统一样本不足、停止线和否词权限。
3. `L-005`：修复 65–69 分重叠。
4. `L-006`、`L-007`、`L-008`、`L-009`：建立互斥状态机及动作仲裁。
5. `L-010`：补齐唯一对象、当前值、目标值、Action_ID 和回滚字段。
6. `L-011`：增加独立验收器；未 PASS 的方案不进入执行单。

## 第二批：控制批量动作的整体风险

1. `L-014` 至 `L-018`：Bid、广告位、预算、否词动作统一仲裁和累计影响上限。
2. `L-023`、`L-026`、`L-031`、`L-032`：动作去重、批次总预算和风险聚合审批。
3. `L-035`：幂等、过期检查和执行前状态校验。
4. `L-036`：把 `1 Campaign = 1 Ad Group` 写成导入硬校验。
5. `L-037`：增加跨报表对账标准。

## 第三批：清理口径与配置债务

处理 `L-038` 至 `L-049`，并为所有边界、版本和字段建立自动化回归测试。

---

# E. 最低回归测试集

开发修改完成后，至少覆盖以下测试：

1. 每套 CVR/ACOS/CPA 阈值的边界值、空档和唯一命中测试。
2. `O=0/1/2` 与各品类点击、花费停止线的组合测试。
3. 词根优化分从 0 到 100 的唯一等级测试。
4. 用户目标线宽于、等于、严于品类风险线的状态测试。
5. 整体状态所有条件组合的全覆盖测试。
6. ACOS 改善、CVR 恶化等混合趋势测试。
7. 同一 Target 同时满足提 Bid 与降 Bid 条件时的仲裁测试。
8. 同一搜索词多词根归属时的动作去重测试。
9. 同一批次多 Campaign、多渠道拓量的总预算和累计影响测试。
10. 缺 Campaign_ID、Target_ID、当前值、回滚值时的 BLOCK 测试。
11. 后台当前值与方案快照不一致时的过期阻断测试。
12. 汇总表与每日明细、Target、Campaign、广告位报表超出允许误差时的对账阻断测试。
13. `1 Campaign != 1 Ad Group` 的异常导入阻断测试。
14. 未通过最终验收时只输出候选、不输出执行动作的测试。

