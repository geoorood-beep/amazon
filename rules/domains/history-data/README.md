# Rug 历史效果数据规则

本模块只管理 Rug 历史效果证据，不是老品诊断报表模块。

## 当前固定来源

[标准化 Rug 历史效果词表](../../../reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx)

当前源表是关键词分析汇总，不是 Amazon Customer Search Term Report。legacy `search_term` 必须按 `TARGETING_KEYWORD` 解释。

## 读取顺序

1. [文件、字段、证据粒度和入库](schema-and-ingest.md)；
2. [新品、新广告和老品候选词的使用边界](usage-boundaries.md)；
3. [当前报表、ABA、历史和阈值的优先级](../../../knowledge/README.md)；
4. [Rug 历史数据 metadata](../../../reference/category-history/rug/metadata.md)。
