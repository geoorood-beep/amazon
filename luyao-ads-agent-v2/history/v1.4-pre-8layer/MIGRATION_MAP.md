# V1.4 八层拆分迁移索引

本表只帮助人工从旧全文找到当前维护位置。旧文件为 `HISTORICAL_ONLY`；当前语义以右列文件为准。

| 旧文件 / 章节 | 当前落点 | 迁移处理 |
|---|---|---|
| `AGENTS.md` 项目边界、读取顺序、V2 边界 | `AGENTS.md`、`architecture/`、`rules/core/scope-and-capability.md` | 总入口只保留硬边界和路由 |
| `AGENTS.md` 默认数据源 | `knowledge/README.md`、`rules/domains/new-product/scope-input-sources.md` | 从规则中抽出数据源和证据粒度 |
| `AGENTS.md` 数据质量、低样本、唯一状态、趋势、仲裁 | `rules/core/`、`thresholds/rug/governance.md`、`thresholds/rug/performance.md` | 判断逻辑和数值分存 |
| `rug-category.md` 全部 | `rules/domains/rug-category.md`、`thresholds/rug/size-routing.md`、`knowledge/README.md` | 类目入口、尺寸路由、数据源分开 |
| `new-product-promotion.md` 范围、输入、ABA 文件 | `rules/domains/new-product/scope-input-sources.md` | 保留 Rug 模板字段和场景映射 |
| `new-product-promotion.md` 属性冲突、动物图案、选词流程 | `rules/domains/new-product/attribute-and-selection.md` | 只保留判断顺序，数值引用阈值文件 |
| `new-product-promotion.md` 阶段、评分、ABA 分组 | `thresholds/rug/new-product-stage.md` | 可调整数值集中维护 |
| `new-product-promotion.md` 广告类型、匹配、命名 | `rules/domains/new-product/architecture.md` | 广告架构规则独立 |
| `new-product-promotion.md` 精准否定和高流量隔离 | `rules/domains/new-product/negative-isolation.md`、`thresholds/rug/budget-and-isolation.md` | 资格数值与权限分存 |
| `new-product-promotion.md` 输出字段 | `contracts/new-product-output.md`、`rules/output/README.md` | 字段合同与输出规则分开 |
| `old-product-promotion.md` 报表和有限模式 | `contracts/data-input.md`、`rules/domains/old-product/input-and-modes.md` | 报表名称是合同，模式权限是规则 |
| `old-product-promotion.md` 数据质量和唯一状态 | `rules/core/data-quality.md`、`rules/core/overall-state.md` | 不在老品文件重复定义 |
| `old-product-promotion.md` 诊断路径、预算、Bid、广告位 | `rules/domains/old-product/diagnosis.md`、`budget-bid-placement.md` | 按局部模块拆分 |
| `old-product-promotion.md` 广告商品和趋势 | `rules/domains/old-product/product-and-trend.md`、`rules/core/trend-placement-budget.md` | 业务诊断与核心权限分开 |
| `old-product-promotion.md` 搜索词、拓量、结构 | `rules/domains/search-term/`、`rules/domains/old-product/growth-and-structure.md` | 词根仍只有一套规则 |
| `old-product-promotion.md` 仲裁、Validator、执行顺序 | `rules/core/action-arbitration-validator.md`、`contracts/action-and-plan.md` | 核心执行安全独立 |
| `search-term-reinvestment.md` 语义模型和 ABA 多归属 | `rules/domains/search-term/semantic-aggregation.md` | 当前唯一词根规则源 |
| `search-term-reinvestment.md` 评分、放大、拓量数值 | `thresholds/rug/traffic-and-scoring.md` | 评分数值不留在规则文件 |
| `search-term-reinvestment.md` 动作、否词、去重 | `rules/domains/search-term/scoring-and-actions.md`、`rules/core/sample-and-attribution.md` | 候选权限和低样本门分存 |
| `category-traffic-strategy.md` 范围和输入 | `rules/domains/category-traffic/scope-and-input.md` | 类目级和产品级边界保留 |
| `category-traffic-strategy.md` 相关性、标准化、竞对分层 | `rules/domains/category-traffic/relevance-and-segmentation.md` | 非标 Rug 竞对仍是弱参考 |
| `category-traffic-strategy.md` N/G 和结构数值 | `thresholds/rug/traffic-and-scoring.md` | 数值和公式集中 |
| `category-traffic-strategy.md` 打法、输出、置信度 | `rules/domains/category-traffic/structure-and-playbook.md`、`output-and-confidence.md` | 打法与输出拆开 |
| `category-history-data.md` 文件、字段、有效性和入库 | `rules/domains/history-data/schema-and-ingest.md` | 增加 `evidence_grain`，修复 legacy `search_term` 语义 |
| `category-history-data.md` 新品调用、复用和禁区 | `rules/domains/history-data/usage-boundaries.md`、`knowledge/README.md` | 不得启用当前链接老品动作 |
| `category data thresholds.md` 全部数值 | `thresholds/rug/` | 按来源、治理、尺寸、性能、新品和待确认拆分 |
| `promo-output-templates.md` 命名和可读说明 | `rules/output/README.md`、`rules/domains/new-product/architecture.md` | 输出行为与字段合同分开 |
| `promo-output-templates.md` 新品/老品字段 | `contracts/new-product-output.md`、`contracts/old-product-output.md`、`contracts/action-and-plan.md` | 字段只在合同中维护 |

迁移不代表历史文字全部继续生效。与 Rug-only、当前证据粒度、单一真源或 V2 安全门冲突的旧描述已按右列当前文件修正。
