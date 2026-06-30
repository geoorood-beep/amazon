# Amz Listing

Amazon Listing 智能体规则仓库。

本仓库固定保存 `listing智能体` 项目的 AGENTS 规则，用于指导 Codex 按多类目架构生成 Amazon Listing：

- `rug`
- `chair`
- `pet_water_fountain`

入口文件：

- `AGENTS.md`
- `agents/listing-generation.md`
- `agents/category-routing.md`
- `agents/keyword-library-contract.md`
- `agents/risk-cdq-audit.md`
- `agents/categories/*.md`

注意：本仓库只保存 AGENTS 规则文档，不保存 `.env.local`、OpenAI API Key、`node_modules`、Next.js build 产物或完整词库数据。

