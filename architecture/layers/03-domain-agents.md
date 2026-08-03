# 第 03 层：Multi-Agent 领域协作

## 领域模块

| 模块 | 唯一职责 | 规则正文直达 |
|---|---|---|
| Rug 类目入口 | 尺寸类型与数据边界 | [类目边界正文](../../rules/domains/rug-category.md) |
| 新品推广 | 属性过滤、选词和人工广告架构 | [输入](../../rules/domains/new-product/scope-input-sources.md)、[选词](../../rules/domains/new-product/attribute-and-selection.md)、[架构](../../rules/domains/new-product/architecture.md)、[隔离](../../rules/domains/new-product/negative-isolation.md) |
| 老品推广 | 当前链接诊断、候选动作和新结构判断 | [输入模式](../../rules/domains/old-product/input-and-modes.md)、[诊断](../../rules/domains/old-product/diagnosis.md)、[预算/Bid/广告位](../../rules/domains/old-product/budget-bid-placement.md)、[趋势](../../rules/domains/old-product/product-and-trend.md)、[拓量](../../rules/domains/old-product/growth-and-structure.md) |
| 搜索词 | 词根语义聚合、评分与复投候选 | [语义聚合](../../rules/domains/search-term/semantic-aggregation.md)、[评分与动作](../../rules/domains/search-term/scoring-and-actions.md) |
| 类目流量 | 入口数量、集中度和打法方向 | [输入](../../rules/domains/category-traffic/scope-and-input.md)、[分层](../../rules/domains/category-traffic/relevance-and-segmentation.md)、[打法](../../rules/domains/category-traffic/structure-and-playbook.md)、[输出](../../rules/domains/category-traffic/output-and-confidence.md) |
| 历史数据 | Rug 历史效果词入库和证据边界 | [字段与入库](../../rules/domains/history-data/schema-and-ingest.md)、[使用边界](../../rules/domains/history-data/usage-boundaries.md) |
| 输出 | 两张表、执行字段和设计逻辑 | [输出规则正文](../../rules/output/output-rules.md) |

## 协作原则

1. 一个结论只能有一个领域模块负责。
2. 搜索词模块是老品诊断的子模块，不是老品总入口。
3. 类目流量模块只判断市场入口，不替代产品级选词。
4. 历史效果词只提供候选证据，不替代当前链接报表。
5. 多模块任务按 Rug 入口、新品/老品主模块、搜索词、流量、历史、输出的顺序合并。
6. 模块冲突时先按[动作仲裁和 Validator 正文](../../rules/core/action-arbitration-validator.md)仲裁；无法安全仲裁则阻断。
