# 领域规则：Rug 类目入口

## 允许对象

- area rug；
- runner rug；
- doormat / entry rug；
- bathroom rug；
- kitchen rug；
- outdoor rug；
- round rug；
- 其他明确属于 Rug 的产品。

## 固定数据直达

- ABA：[Area Excel](../../reference/rug-aba/area_rug_ABA关键词库_202605_v8.xlsx)、[Bathroom Excel](../../reference/rug-aba/bathroom_rugs_ABA关键词库_202605.xlsx)、[Kitchen Excel](../../reference/rug-aba/kitchen_rugs_ABA关键词库_202605_v2.xlsx)、[Outdoor Excel](../../reference/rug-aba/outdoor_rug_ABA关键词库_202605_v2.xlsx)；
- 历史效果：[标准化历史效果词 Excel](../../reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx)；
- 阈值：[尺寸路由](../../thresholds/rug/size-routing.md)、[性能阈值](../../thresholds/rug/performance.md)、[新品阶段](../../thresholds/rug/new-product-stage.md)、[预算隔离](../../thresholds/rug/budget-and-isolation.md)；
- 边界配置：[project_scope.json](../../config/project_scope.json)。

## 处理顺序

1. 确认目标推广尺寸和产品形态；
2. 按[尺寸与类型路由](../../thresholds/rug/size-routing.md)识别类型；
3. 按产品场景选择 ABA 文件，只读 `广告词库`；
4. 新品进入[新品规则](new-product/README.md)；
5. 当前链接稳定广告数据进入[老品规则](old-product/README.md)；
6. 需要市场入口判断时进入[类目流量规则](category-traffic/README.md)。

圆形阈值未配置时，性能判断和标准预算阻断，不得借用其他类型。
