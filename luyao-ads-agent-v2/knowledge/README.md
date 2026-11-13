# Rug 知识与数据源导航

当前规则版本：`V2.0`

本页只定义读取优先级和证据粒度，不保存广告动作规则或阈值。人工点击链接使用当前电脑绝对路径，直接打开具体数据文件或阈值正文。

## 来源优先级

| 优先级 | 来源 | 可以证明什么 | 不能证明什么 |
|---:|---|---|---|
| 1 | 用户本次提供的当前链接真实报表 | 当前 Campaign / Ad Group / Target / 搜索词 / Placement 表现 | 其他链接和其他日期的表现 |
| 2 | 当前链接历史搜索词报表 | 当前链接买家查询和有限趋势 | 完整后台结构，除非同时有 Targeting 和设置表 |
| 3 | [Area ABA Excel](/Users/leo/Documents/陆遥广告智能体/reference/rug-aba/area_rug_ABA关键词库_202605_v8.xlsx)<br>[Bathroom ABA Excel](/Users/leo/Documents/陆遥广告智能体/reference/rug-aba/bathroom_rugs_ABA关键词库_202605.xlsx)<br>[Kitchen ABA Excel](/Users/leo/Documents/陆遥广告智能体/reference/rug-aba/kitchen_rugs_ABA关键词库_202605_v2.xlsx)<br>[Outdoor ABA Excel](/Users/leo/Documents/陆遥广告智能体/reference/rug-aba/outdoor_rug_ABA关键词库_202605_v2.xlsx) | 市场词、ABA 排名、属性和合规标签 | 当前链接真实订单和实际匹配 |
| 4 | [Rug 标准化历史效果词 Excel](/Users/leo/Documents/陆遥广告智能体/reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx) | 同类历史投放关键词效果候选 | Customer Search Term、当前链接动作 |
| 5 | [新品相关性表字段模板](../config/new_product_relevance.example.csv)<br>[搜索词月搜索量字段模板](../config/new_product_search_volume.example.csv) | 补表后证明 ASIN 相关性、词根需求和分布 | 正式数据放入 `reference/rug-relevance/` 与 `reference/rug-search-volume/`；当前为 `PENDING_SOURCE`，不能先行判定 Phrase/Broad |
| 6 | [拆分前 AGENTS 原文](/Users/leo/Documents/陆遥广告智能体/history/v1.4-pre-8layer/AGENTS.md) | 旧规则追溯 | 当前有效规则 |

## 固定 ABA

默认四个文件：

- [Area Rug ABA](/Users/leo/Documents/陆遥广告智能体/reference/rug-aba/area_rug_ABA关键词库_202605_v8.xlsx)
- [Bathroom Rug ABA](/Users/leo/Documents/陆遥广告智能体/reference/rug-aba/bathroom_rugs_ABA关键词库_202605.xlsx)
- [Kitchen Rug ABA](/Users/leo/Documents/陆遥广告智能体/reference/rug-aba/kitchen_rugs_ABA关键词库_202605_v2.xlsx)
- [Outdoor Rug ABA](/Users/leo/Documents/陆遥广告智能体/reference/rug-aba/outdoor_rug_ABA关键词库_202605_v2.xlsx)

只读取各文件 `广告词库` sheet。不同场景不得混成无边界全量池。

跨文件同词出现类型、层级、相关度、合规或广告状态冲突时采用保守隔离，不随机选择一个来源覆盖。

## 历史效果

当前固定 Rug 文件是[标准化历史效果词表](/Users/leo/Documents/陆遥广告智能体/reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx)。legacy `search_term` 是关键词分析汇总中的投放/效果关键词，适配时标记 `TARGETING_KEYWORD`。它没有独立成交日期、Campaign、Ad Group 或真实匹配方式证据。

## 阈值

具体数字直接读取：[性能阈值](/Users/leo/Documents/陆遥广告智能体/thresholds/rug/performance.md)、[新品阶段](/Users/leo/Documents/陆遥广告智能体/thresholds/rug/new-product-stage.md)、[预算与隔离](/Users/leo/Documents/陆遥广告智能体/thresholds/rug/budget-and-isolation.md)、[新品 Phrase/Broad 路由](/Users/leo/Documents/陆遥广告智能体/thresholds/rug/match-type-routing.md)、[归因与趋势](/Users/leo/Documents/陆遥广告智能体/thresholds/rug/governance.md)、[尺寸路由](/Users/leo/Documents/陆遥广告智能体/thresholds/rug/size-routing.md)、[流量与评分](/Users/leo/Documents/陆遥广告智能体/thresholds/rug/traffic-and-scoring.md)。不得从 ABA、历史平均值或旧 Markdown 自动推导阈值。

## 当前链接真实报表

报表标准名称和字段见[数据输入合同](/Users/leo/Documents/陆遥广告智能体/contracts/data-input.md)。数据快照必须保存来源文件和 SHA-256。
