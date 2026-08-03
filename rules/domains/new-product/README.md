# 新品推广规则入口

新品模块只为 Rug 生成选词和人工广告架构，不执行 Amazon 后台动作，也不表示 V2 `SP_COLD_START` 已激活。

## 读取顺序

1. [范围、用户输入和 ABA 数据源](scope-input-sources.md)；
2. [属性硬冲突与选词](attribute-and-selection.md)；
3. [广告架构、分组和命名](architecture.md)；
4. [精准否定与隔离](negative-isolation.md)；
5. [输出规则正文](../../output/output-rules.md)。

数值只读：

- [尺寸与 Rug 类型路由](../../../thresholds/rug/size-routing.md)；
- [新品订单阶段和 ABA 区间](../../../thresholds/rug/new-product-stage.md)；
- [标准预算和高流量隔离](../../../thresholds/rug/budget-and-isolation.md)；
- [CVR、ACOS、CPA 性能阈值](../../../thresholds/rug/performance.md)。

数据直达：[Area ABA Excel](../../../reference/rug-aba/area_rug_ABA关键词库_202605_v8.xlsx)、[Bathroom ABA Excel](../../../reference/rug-aba/bathroom_rugs_ABA关键词库_202605.xlsx)、[Kitchen ABA Excel](../../../reference/rug-aba/kitchen_rugs_ABA关键词库_202605_v2.xlsx)、[Outdoor ABA Excel](../../../reference/rug-aba/outdoor_rug_ABA关键词库_202605_v2.xlsx)、[历史效果词 Excel](../../../reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx)。字段直达：[新品输出合同正文](../../../contracts/new-product-output.md)。

## 输出

- `ABA选词表`；
- `新广告设置表`；
- 第一张表下方的 `判断依据与设计逻辑`。
