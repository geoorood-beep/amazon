# 搜索词与词根规则入口

本目录是项目内 ABA 词根匹配集合的唯一当前规则源。老品诊断和单独的词根聚合必须读取同一结果。

## 读取顺序

1. [语义槽位、Phrase/Broad/Exact 和 ABA 多归属](semantic-aggregation.md)；
2. [评分选择、候选动作、否词和去重](scoring-and-actions.md)；
3. [机会分、词根分、放大和拓量数值](../../../thresholds/rug/traffic-and-scoring.md)；
4. [性能档与低样本数值](../../../thresholds/rug/performance.md)；
5. [低样本、归因和否词权限](../../core/sample-and-attribution.md)。

## 数据和字段直达

- [Area ABA Excel](../../../reference/rug-aba/area_rug_ABA关键词库_202605_v8.xlsx)
- [Bathroom ABA Excel](../../../reference/rug-aba/bathroom_rugs_ABA关键词库_202605.xlsx)
- [Kitchen ABA Excel](../../../reference/rug-aba/kitchen_rugs_ABA关键词库_202605_v2.xlsx)
- [Outdoor ABA Excel](../../../reference/rug-aba/outdoor_rug_ABA关键词库_202605_v2.xlsx)
- [Rug 历史效果词 Excel](../../../reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx)
- [当前链接报表字段](../../../contracts/data-input.md)
- [有限/完整老品输出](../../../contracts/old-product-output.md)

只有类目历史效果词而没有当前链接搜索词时，只输出选词参考。完整搜索词 ABA 排名不得继承词根排名；后台实际匹配方式必须由 Targeting 报表确认。
