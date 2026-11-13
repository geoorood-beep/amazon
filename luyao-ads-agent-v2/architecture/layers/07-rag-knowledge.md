# 第 07 层：RAG 知识检索

## 检索优先级

```text
用户本次提供的当前链接真实报表
→ 当前链接历史搜索词报表
→ 本项目固定 Rug ABA
→ Rug 历史 TARGETING_KEYWORD 效果数据
→ 历史归档，仅用于追溯
```

阈值数字直接读取：[性能](../../thresholds/rug/performance.md)、[新品阶段](../../thresholds/rug/new-product-stage.md)、[预算与隔离](../../thresholds/rug/budget-and-isolation.md)、[治理](../../thresholds/rug/governance.md)、[尺寸路由](../../thresholds/rug/size-routing.md)、[流量与评分](../../thresholds/rug/traffic-and-scoring.md)。不得从 ABA、历史效果或旧 Markdown 推导。

固定数据直接读取：[Area ABA Excel](../../reference/rug-aba/area_rug_ABA关键词库_202605_v8.xlsx)、[Bathroom ABA Excel](../../reference/rug-aba/bathroom_rugs_ABA关键词库_202605.xlsx)、[Kitchen ABA Excel](../../reference/rug-aba/kitchen_rugs_ABA关键词库_202605_v2.xlsx)、[Outdoor ABA Excel](../../reference/rug-aba/outdoor_rug_ABA关键词库_202605_v2.xlsx)、[历史效果词 Excel](../../reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx)。

## 证据粒度

- ABA：市场词、排名和属性标签；
- `TARGETING_KEYWORD` 历史效果：同类候选参考；
- Customer Search Term：真实买家查询；
- Targeting 报告：实际投放对象和匹配方式；
- Campaign / Ad Group 设置：预算、Bid、状态和对象映射；
- Placement：广告位表现。

不同粒度不能互相冒充。当前链接真实报表的名称、字段和快照要求见[数据输入合同正文](../../contracts/data-input.md)。
