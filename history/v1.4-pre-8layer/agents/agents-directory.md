# AGENT: 陆遥广告智能体目录

当用户输入 `AGENTS 目录` 时，展示本表。

| AGENT | 作用 | 固定数据 | 缺失影响 | 默认输出 |
|---|---|---|---|---|
| `AGENTS.md` | 项目边界、路由、V1.4 安全门与 V2.0 实施边界 | `config/project_scope.json`、V2 来源 SHA-256 | 非 Rug、来源校验失败或机器规则未激活时停止 | 路由、权限与运行状态 |
| `agents/rug-category.md` | Rug 类目、尺寸、数据映射入口 | Rug ABA、Rug 历史词、阈值原件 | 尺寸或类型不明时阈值阻断 | Rug 类目数据说明 |
| `agents/new-product-promotion.md` | Rug 新品选词与广告架构 | `reference/rug-aba/`、Rug 历史词 | 缺属性时冲突词待确认；圆形阈值阻断 | ABA选词表、新广告设置表 |
| `agents/old-product-promotion.md` | Rug 老品完整诊断 | 当前链接六类真实报表 | 关键报表或唯一 ID 缺失时 `DQ_BLOCKED` | 策略摘要、老广告优化、新广告设置 |
| `agents/search-term-reinvestment.md` | Rug 搜索词、词根、ABA 多归属 | 当前搜索词、Rug ABA | 无 ABA 不编排名；无 Target 不执行否词 | 聚合表与候选动作 |
| `agents/category-traffic-strategy.md` | Rug 类目入口结构 | 对应 Rug ABA 的 `广告词库` 或用户新 Rug 表 | 缺 ABA 不能判断头部结构；禁止跨项目取数 | Rug 类目打法 |
| `agents/category-history-data.md` | Rug 历史效果词入库与调用 | `reference/category-history/rug/` | 固定文件仅为 `TARGETING_KEYWORD` 粒度，不能证明真实搜索词或匹配方式 | 历史证据粒度与置信度 |
| `agents/category data thresholds.md` | Rug 尺寸阈值路由 | 已确认门垫、长条、小区域、大区域阈值 | 圆形固定 `BLOCKED`；O<2 强收缩缺 Threshold ID 时阻断 | 阈值命中与预算依据 |
| `agents/promo-output-templates.md` | 表格、七段命名、设计逻辑 | 上述判断结果 | 数据不足只输出缺失影响 | 两张核心表 / Markdown |
