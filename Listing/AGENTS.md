# Listing 智能体规则仓库

本仓库保存 Amazon、Walmart 与 Wayfair Listing 智能体的 AGENTS 规则。后续 Codex 在这个仓库工作时，必须先判断平台，再读取对应平台的规则文件。

本仓库只保存规则文档和确定性验证/helper scripts，不保存 `.env.local`、API Key、`node_modules`、Next.js build 产物，也不保存完整生产词库数据。

## 平台路由

### Amazon Listing

当任务涉及 Amazon、亚马逊、Amazon US、Title / Bullet Points / Product Description / Search Terms / CDQ / `$listing` 时，先判断是否命中 **Amazon US cat/dog non-food / non-supplement / non-drug hardware/goods V3**。

#### Amazon US pet hardware/goods V3 优先路由

命中以下全部条件时，必须先走 `pet-listing-agent/`：

- 平台：Amazon US
- 物种：cat 或 dog
- 商品性质：non-food、non-supplement、non-drug 的 hardware/goods

命中 V3 时，先读取：

1. `pet-listing-agent/AGENTS.md`
2. `pet-listing-agent/CHANGES.md`
3. `pet-listing-agent/references/category-pet.md`
4. `pet-listing-agent/references/intake-template.md`
5. `pet-listing-agent/references/limits.md`

V3 输出固定顺序为：`主标题 -> 亮点 -> 五点描述 -> 详情文案 -> 简要总结`。

关键词只选 3-5 个 core keywords。

硬性长度 gate：

- 主标题 <= 75 characters
- 亮点 <= 125 characters
- 五点描述每条 <= 256 characters，五点合计 <= 1000 characters
- 详情文案 <= 2000 characters

确定性验证是必须项：`pet-listing-agent/scripts/validate.py` 必须检查每一份实际生成的 draft；`tests/run_tests.py` 只运行测试套件，不能替代 draft 校验。从 `Listing/pet-listing-agent/` 目录按 package 文档中的确切 CLI 运行，不要自行发明 validator flags。

对于已经识别或疑似 pet 商品的 scoped task，以下情况不要自动 V3，也不要自动 fallback 到 `rug`：

- 非 Amazon US 站点
- 非 cat / dog 物种，例如 small animal / bird / reptile / fish 等
- food / supplement / drug / medicinal pet products
- 无法确认商品性质是否属于 non-food hardware/goods

这些情况必须进入澄清 / `Needs manual confirmation`。非 pet 的 legacy `rug` / `chair` 等任务保持原有流程不变。

未命中 V3 的 Amazon 任务，继续读取旧 Amazon 流程：

1. `AGENTS.md`
2. `agents/listing-generator-architecture.md`
3. `agents/category-routing.md`
4. `agents/keyword-library-contract.md`
5. `agents/listing-generation.md`
6. `agents/output-contract.md`
7. `agents/risk-cdq-audit.md`
8. 对应类目文件：
   - `agents/categories/rug.md`
   - `agents/categories/chair.md`
   - `agents/categories/pet-water-fountain.md`
   - 新类目参考 `agents/categories/new-category-template.md`
9. 如果任务涉及本地 Web App、API、前端高亮、fallback 生成或代码实现，再读 `agents/web-app-implementation.md`

Amazon 当前支持类目：

- `rug`
- `chair`
- `pet_water_fountain`
- `pet_hardware_goods_v3`（仅 Amazon US cat/dog non-food / non-supplement / non-drug hardware/goods，文档分发标签，路由到 `pet-listing-agent/`，不是旧 app 实现的类目）

Amazon 的核心数据源设计：

- `amazon-listing-webapp/data/categoryKeywordData.json`
- `amazon-listing-webapp/lib/categoryKeywordRouting.ts`
- `amazon-listing-webapp/lib/localListingGenerator.ts`
- `amazon-listing-webapp/lib/audit.ts`

Amazon 的 AGENTS 目标是替代旧的 `$listing` 生成器说明层：规则、类目路由、词库契约、输出格式和 CDQ 审核必须在 AGENTS 中固定；词库数据仍通过项目数据文件或 AGENTS 完整安装包提供，不把长表内容复制进 Markdown 正文。

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
10. 对于 Amazon US cat/dog non-food / non-supplement / non-drug hardware/goods 的 scoped task，`pet-listing-agent` V3 输出顺序、长度 gate、3-5 核心关键词选择和 `scripts/validate.py` 确定性验证优先于旧 Amazon `Title` / `Item Highlights` / `Bullet Points` / `Product Description` / `Search Terms` 通用生成规则。

## 修改规则

- 改 Amazon 规则，只动 `agents/` 下 Amazon 相关文件。
- 改 Walmart 规则，只动 `agents/walmart/` 下 Walmart 相关文件。
- 改 Wayfair 规则，只动 `agents/wayfair/` 下 Wayfair 相关文件。
- 如果要新增 Amazon 类目，按 `agents/categories/new-category-template.md` 增加类目说明，并按 `agents/keyword-library-contract.md` 准备关键词库和风险库。
- 如果要新增 Walmart 类目，按 `agents/walmart/categories/new-category-template.md` 增加类目说明，并按 `agents/walmart/knowledge-base-contract.md` 准备关键词表。
- 如果未来引入代码实现，必须保留 prepare -> draft JSON -> audit 的确定性发布链路。
- `pet-listing-agent/` 内文件本次更新保持包内原样，当前改动不改动该 package；需要适配时只改上层 routing / summary 文档，不做 seller backend 改动或部署。
- `pet-listing-agent` 文本若引用 `keyword-data-contract.md` 或 `knowledge-bases/pet`，这些文件不在当前包内，也不是本仓库 shipped sources。实际关键词契约是 `agents/keyword-library-contract.md`；`knowledge-bases/pet` 只在外部提供并显式挂载时可用。不得伪造词库文件或声称缺失数据已存在。
