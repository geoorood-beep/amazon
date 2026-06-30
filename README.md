# Amz Listing

Listing 智能体规则仓库。

本仓库固定保存 Amazon 与 Walmart Listing 的 AGENTS 规则，用于指导 Codex 按平台、类目、关键词库和风险库生成合规 Listing。

## 已支持平台

### Amazon

Amazon AGENTS 入口：

- `AGENTS.md`
- `agents/listing-generation.md`
- `agents/category-routing.md`
- `agents/keyword-library-contract.md`
- `agents/risk-cdq-audit.md`
- `agents/categories/*.md`

当前 Amazon 类目：

- `rug`
- `chair`
- `pet_water_fountain`

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

## 仓库边界

本仓库只保存 AGENTS 规则文档，不保存：

- `.env.local`
- OpenAI API Key
- `node_modules`
- Next.js build 产物
- 完整生产词库数据
- 客户敏感数据
