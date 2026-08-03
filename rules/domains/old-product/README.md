# 老品推广规则入口

老品模块使用当前 Rug 链接真实报表做完整诊断，同时判断老广告优化和新广告结构。

## 读取顺序

1. [输入报表和完整/有限模式](input-and-modes.md)；
2. [固定诊断顺序](diagnosis.md)；
3. [预算、Bid 和 Placement](budget-bid-placement.md)；
4. [广告商品和趋势](product-and-trend.md)；
5. 需要搜索词时读取[搜索词与词根规则](../search-term/README.md)；
6. [跨广告产品拓量和结构](growth-and-structure.md)；
7. [输出规则正文](../../output/output-rules.md) 与[老品输出合同](../../../contracts/old-product-output.md)；
8. [动作仲裁和 Validator](../../core/action-arbitration-validator.md)。

老品必须同时回答“现有广告如何处理”和“是否需要新建、并入或重建”。当前链接报表优先于 ABA 和类目历史证据。

数值直达：[性能阈值](../../../thresholds/rug/performance.md)、[归因与趋势阈值](../../../thresholds/rug/governance.md)、[评分与拓量门](../../../thresholds/rug/traffic-and-scoring.md)、[待确认动作参数](../../../thresholds/rug/pending.md)。

数据/合同直达：[老品报表与快照字段](../../../contracts/data-input.md)、[完整动作与回滚](../../../contracts/action-and-plan.md)、[数据源优先级](../../../knowledge/README.md)。
