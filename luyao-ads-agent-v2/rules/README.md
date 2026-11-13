# 当前规则目录

当前规则版本：`V2.0`

本目录是当前人工可读规则的唯一正文。规则只写“何时判断、按什么顺序、有什么权限”，不保存可调整数值。

## 核心规则

| 文件 | 维护内容 |
|---|---|
| [作用域与能力](core/scope-and-capability.md) | Rug 边界、广告产品和能力状态 |
| [数据质量](core/data-quality.md) | DQ 状态、对象映射和有限数据权限 |
| [样本与归因](core/sample-and-attribution.md) | 低样本、归因成熟和否词权限 |
| [唯一整体状态](core/overall-state.md) | 唯一整体状态优先级 |
| [趋势、Placement 与预算](core/trend-placement-budget.md) | 趋势、广告位和预算压力路由 |
| [动作仲裁与 Validator](core/action-arbitration-validator.md) | 动作去重、冲突、回滚和 Validator |

## 领域规则

| 任务 | 唯一入口 |
|---|---|
| Rug 类目与尺寸 | [进入规则](domains/rug-category.md) |
| 广告架构设计 | [进入新品架构规则](domains/new-product/README.md) |
| SP广告优化 | [进入 SP 优化规则](domains/old-product/README.md) |
| 搜索词与词根 | [进入搜索词规则](domains/search-term/README.md) |
| 类目流量结构 | [进入流量结构规则](domains/category-traffic/README.md) |
| 历史数据 | [进入历史数据规则](domains/history-data/README.md) |
| 输出 | [输出规则正文](output/output-rules.md) |

需同时查数值时，从[阈值目录](../thresholds/README.md)进入；需查固定文件时，从[数据源目录](../knowledge/README.md)进入。

## 规则修改约束

1. 新增规则必须分配稳定 Rule ID；当前仍在人工迁移的规则可以先标 `RULE_ID_PENDING`，但不能进入机器执行。
2. 规则引用数值时只写 Threshold ID 和链接，不复制数值。
3. 规则正文不得写在 `agents/` 兼容入口或 `history/`。
4. 修改规则后必须检查引用的阈值和合同是否存在。
5. 当前没有生产机器 `ACTIVE` 规则包；本目录是 `HUMAN_EXECUTION_ONLY` 人工规则集。
