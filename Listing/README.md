# UTA-amazon Listing

Listing 智能体规则仓库。

本仓库固定保存 Amazon、Walmart 与 Wayfair Listing 的 AGENTS 规则，用于指导 Codex 按平台、类目、关键词库和风险库生成合规 Listing。

## 已支持平台

### Amazon

Amazon AGENTS 入口：

- `AGENTS.md`
- `agents/listing-generator-architecture.md`
- `agents/listing-generation.md`
- `agents/category-routing.md`
- `agents/keyword-library-contract.md`
- `agents/output-contract.md`
- `agents/risk-cdq-audit.md`
- `agents/web-app-implementation.md`
- `agents/categories/*.md`

当前 Amazon 类目：

- `rug`
- `chair`
- `pet_water_fountain`

Amazon Listing 生成器已经按 AGENTS 拆分为：

- 平台路由
- 类目路由
- 关键词库 / 风险库契约
- 生成流程
- 输出格式
- CDQ 审核
- 本地 Web App 实现边界

完整可迁移安装包可以额外携带 `knowledge-bases/amazon/` 下的来源表和转换后的 CSV。GitHub 规则仓库不强制保存完整生产词库。

### Walmart

Walmart AGENTS 入口：

- `agents/walmart/index.md`
- `agents/walmart/category-routing.md`
- `agents/walmart/knowledge-base-contract.md`
- `agents/walmart/generation-workflow.md`
- `agents/walmart/risk-audit.md`
- `agents/walmart/categories/*.md`

当前 Walmart 已沉淀类目：

- `rug`

后续新增 Walmart 类目时，只要按 `agents/walmart/knowledge-base-contract.md` 准备该类目的关键词表 / 风险词表 / 条件规则表，并增加对应类目说明，就可以让同一套流程生成不同类目的 Walmart Listing。

### Wayfair

Wayfair AGENTS 入口：

- `agents/wayfair/AGENTS.md`
- `agents/wayfair/references/rules.md`
- `agents/wayfair/scripts/wayfair_kb.py`
- `agents/wayfair/assets/wayfair_listing_knowledge_base.xlsx`

Wayfair 规则固定输出 `Title1`、`Title2`、`Title3`、`Marketing Copy`、`Feature Bullets`、`Keyword / Attribute Usage Summary: Pattern&Colors`、`Blocked Input / Risk Screening`、`Wayfair Audit`。标题结构必须是 `Machine Washable + Pattern + Color + Doormat/Hallway Runner/Area Rug + With Non-Slip Backing`，且 `With Non-Slip Backing` 后不能再加词。

## 仓库边界

本仓库只保存 AGENTS 规则文档，不保存：

- `.env.local`
- OpenAI API Key
- `node_modules`
- Next.js build 产物
- Amazon / Walmart 完整生产词库数据
- 客户敏感数据

Wayfair 例外：`agents/wayfair/assets/wayfair_listing_knowledge_base.xlsx` 是 Wayfair 生成器运行必需的规则和关键词 workbook，已随仓库保存，避免依赖任何本机 skill 安装路径。
