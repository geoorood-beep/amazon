# Listing 智能体规则仓库

本仓库保存 Amazon、Walmart 与 Wayfair Listing 智能体的 AGENTS 规则。后续 Codex 在这个仓库工作时，必须先判断平台，再读取对应平台的规则文件。

本仓库只保存规则文档，不保存 `.env.local`、API Key、`node_modules`、Next.js build 产物，也不保存完整生产词库数据。

## 平台路由

### Amazon Listing

当任务涉及 Amazon、亚马逊、Amazon US、Title / Bullet Points / Product Description / Search Terms / CDQ / `$listing` 时，读取：

1. `AGENTS.md`
2. `agents/listing-generation.md`
3. `agents/category-routing.md`
4. `agents/keyword-library-contract.md`
5. `agents/risk-cdq-audit.md`
6. 对应类目文件：
   - `agents/categories/rug.md`
   - `agents/categories/chair.md`
   - `agents/categories/pet-water-fountain.md`

Amazon 当前支持类目：

- `rug`
- `chair`
- `pet_water_fountain`

Amazon 的核心数据源设计：

- `amazon-listing-webapp/data/categoryKeywordData.json`
- `amazon-listing-webapp/lib/categoryKeywordRouting.ts`
- `amazon-listing-webapp/lib/localListingGenerator.ts`
- `amazon-listing-webapp/lib/audit.ts`

### Walmart Listing

当任务涉及 Walmart、沃尔玛、Product Title、Description、Key Features、Frequency Rank、prohibited terms、`$walmart-listing-generator` 时，读取：

1. `AGENTS.md`
2. `agents/walmart/index.md`
3. `agents/walmart/category-routing.md`
4. `agents/walmart/knowledge-base-contract.md`
5. `agents/walmart/generation-workflow.md`
6. `agents/walmart/risk-audit.md`
7. 对应类目文件：
   - `agents/walmart/categories/rug.md`
   - 新类目参考 `agents/walmart/categories/new-category-template.md`

Walmart 的核心设计是：每个类目都有自己的关键词表 / 风险表 / 条件规则表。生成前必须选择类目，再加载该类目的 Walmart knowledge base。

### Wayfair Listing

当任务涉及 Wayfair、威菲尔、`wayfair-listing-generator`、Doormat / Hallway Runner / Area Rug 三标题结构，或标题必须遵循 `Machine Washable + Pattern + Color + Product Type + With Non-Slip Backing` 时，读取：

1. `AGENTS.md`
2. `agents/wayfair/AGENTS.md`
3. `agents/wayfair/references/rules.md`

Wayfair 的核心设计是：使用仓库内置 workbook 作为 Pattern、Color、关键词和规则来源，通过 `agents/wayfair/scripts/wayfair_kb.py` 先 prepare，再 draft JSON，最后 audit。Wayfair 输出不得套用 Amazon 的品牌开头标题、75 字符限制、Item Highlights、5 条 Bullet、Search Terms 或 CDQ 输出结构，也不得套用 Walmart 的 Product Title / Key Features 结构。

## 全局硬规则

1. 用户输入不是豁免项，必须筛查。
2. 先判断平台，再判断类目。
3. 不同平台规则不能混用；Walmart 不使用 Amazon `Search Terms` 规则，Amazon 不使用 Walmart `Key Features` 规则，Wayfair 不使用 Amazon/Walmart 的标题和 bullet 结构。
4. 不同类目的关键词库不能混用。
5. 词库只是候选池，不是自动文案。
6. 禁用词、高危词、竞品词、ASIN、排名词、促销词、保修 / 保证词、医疗 / 疾病词、未证明安全 / 认证词必须拦截。
7. 最终 pass/fail 由确定性审核决定，不能只靠模型判断。
8. 面向客户的 Listing 正文里不要复述被拦截的风险原词。
9. 需要证明的卖点必须写进确认项或阻塞项。

## 修改规则

- 改 Amazon 规则，只动 `agents/` 下 Amazon 相关文件。
- 改 Walmart 规则，只动 `agents/walmart/` 下 Walmart 相关文件。
- 改 Wayfair 规则，只动 `agents/wayfair/` 下 Wayfair 相关文件。
- 如果要新增 Walmart 类目，按 `agents/walmart/categories/new-category-template.md` 增加类目说明，并按 `agents/walmart/knowledge-base-contract.md` 准备关键词表。
- 如果未来引入代码实现，必须保留 prepare -> draft JSON -> audit 的确定性发布链路。
