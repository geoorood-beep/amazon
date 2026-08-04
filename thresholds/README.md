# 当前阈值目录

当前规则版本：`V2.0`。其中标记为 V1.4 的文件名或历史路径只表示来源版本。

本目录是人工可读数值、区间、单位和确认状态的唯一正文。`rules/` 只引用这里，不复制数值。

> 本页是导航，不复制具体数值。查数字时直接点击下方对应文件；不要去[总入口](../AGENTS.md) 或 `rules/` 找阈值。

## 具体数据快速入口

- [CVR、ACOS、CPA 四档及低样本点击/花费锚点](rug/performance.md)
- [新品订单阶段、ABA 区间、评分和广告组分组](rug/new-product-stage.md)
- [标准最低日预算公式和高流量核心隔离门](rug/budget-and-isolation.md)
- [归因成熟期、趋势窗口和小时花费曲线](rug/governance.md)
- [Rug 尺寸、类型和区域面积路由](rug/size-routing.md)
- [类目入口、G 梯度、机会分、词根分和拓量证据](rug/traffic-and-scoring.md)
- [新品 Phrase/Broad 的词根月搜索量和集中度分层](rug/match-type-routing.md)
- [历史数据生成候选阈值的点击、订单、天数和验证窗口门槛](rug/calibration-eligibility.md)
- [待人工补齐的阈值清单](rug/pending.md)
- [阈值原件、SHA-256 和确认状态](rug/source-manifest.md)

## Rug 阈值

| 文件 | 内容 | 当前状态 |
|---|---|---|
| [来源清单](rug/source-manifest.md) | 来源、SHA-256、确认日期和适用范围 | 审计入口 |
| [治理阈值](rug/governance.md) | 归因期、趋势窗口、小时节奏 | 部分确认 / 部分人工规则 |
| [尺寸路由](rug/size-routing.md) | 尺寸类型和区域面积路由 | 人工固定 |
| [性能阈值](rug/performance.md) | CVR、ACOS、CPA 四档和 O<2 锚点 | 非圆形已确认；停止线机器阻断 |
| [新品阶段](rug/new-product-stage.md) | 新品 ABA 阶段、评分和分组 | 人工规则，机器未激活 |
| [预算与隔离](rug/budget-and-isolation.md) | 标准最低预算和新品隔离门 | 人工规则，机器未激活 |
| [流量与评分](rug/traffic-and-scoring.md) | 类目结构与搜索词评分数值 | 人工规则，机器未激活 |
| [Phrase/Broad 路由](rug/match-type-routing.md) | 词根月搜索量、Top3占比和时间窗口 | 用户确认的临时候选标准；待数据回放 |
| [历史校准资格](rug/calibration-eligibility.md) | 2,000/50/14、5,000/100/30/3 和零订单风险门 | 候选生成已启用；人工批准；不自动应用 |
| [待确认清单](rug/pending.md) | 所有未确认数值和启用阻断 | 必须人工补齐 |

## 状态含义

- `CONFIRMED_HUMAN`：已有人工作为当前规则使用的来源证据；不自动等于机器 ACTIVE。
- `HUMAN_RULE_FIXED`：当前人工规则沿用值，但没有生产 Threshold ID 或完整来源裁决。
- `PENDING`：不得使用或推算。
- `BLOCKED_PENDING_THRESHOLD_ID`：可以显示风险提示，但不得形成机器执行动作。

## 修改要求

每次修改必须同时记录：值、单位、开闭边界、适用类目/类型、来源、确认人、确认日期、状态和是否允许机器使用。不能只改 Markdown 数字而不改来源与状态。

每套机器可用阈值还必须声明 `applicable_grain`。允许枚举：`SKU_SIZE`、`ADVERTISED_PRODUCT`、`TARGET`、`SEARCH_TERM`、`PLACEMENT`、`CAMPAIGN`、`ACCOUNT`。没有声明或跨粒度套用时固定阻断；上层聚合必须先汇总原始分子分母，再应用明确属于该层的阈值。
