# Amazon Listing 智能体

本项目用于生成 Amazon Listing / CDQ 内容。所有 Listing 生成必须先判断类目，再调用对应类目的关键词库和风险库，最后通过确定性审核。

本文件和 `agents/` 目录里的文件，是这个项目的固定工作规则。若旧 README 或旧任务说明与这里冲突，以这里为准。

## 必读顺序

只要任务涉及 Listing 生成、审核、类目路由、关键词库、风险库、输出格式或 Web App 逻辑，先按顺序读：

1. `AGENTS.md`
2. `agents/listing-generation.md`
3. `agents/category-routing.md`
4. `agents/keyword-library-contract.md`
5. `agents/risk-cdq-audit.md`
6. 对应类目文件：
   - `agents/categories/rug.md`
   - `agents/categories/chair.md`
   - `agents/categories/pet-water-fountain.md`

## 核心架构

这是一个多类目的 Listing 生成系统。流程必须是：

1. 先判断产品类目。
2. 只加载该类目的关键词库和风险库。
3. 生成 Listing。
4. 做确定性 CDQ / 风险审核。
5. 不合格就重写失败模块。

当前支持类目：

- `rug`
- `chair`
- `pet_water_fountain`

核心文件：

- `amazon-listing-webapp/lib/categoryKeywordRouting.ts`：类目标准化、类目推断、词库选择。
- `amazon-listing-webapp/data/categoryKeywordData.json`：多类目关键词库和风险库的唯一打包数据源。
- `amazon-listing-webapp/data/keywordData.json`：旧版 / 兜底 rug 词库。
- `amazon-listing-webapp/lib/localListingGenerator.ts`：本地 SOP 规则生成器。
- `amazon-listing-webapp/lib/aiListingGenerator.ts`：可选 AI 生成逻辑，但仍要走服务端确定性审核。
- `amazon-listing-webapp/lib/audit.ts`：Title、Item Highlights、五点、Search Terms、风险和 CDQ 审核。
- `amazon-listing-webapp/lib/keywordDataParser.ts`：上传关键词 / 风险词文件后的解析与合并。
- `amazon-listing-webapp/app/api/generate/route.ts`：API 入口，负责加载类目数据并触发生成。

## 不可跳过的硬规则

1. 用户输入也必须筛查，不能因为是用户给的就直接进入 Listing。
2. 原始提示词、上传文件、手工关键词、图片备注、翻译、运营备注都要先过风险筛查。
3. 必须先判断类目，再选关键词。
4. 不同类目的关键词库不能混用。
5. 禁用词、高危词、竞品词、ASIN、排名词、促销价格词、保修/保证词、医疗/疾病词、未证明安全/认证词，必须在草稿前移除。
6. 关键词库只是候选流量数据，不是必须照抄的文案。
7. 只能写产品事实和用户确认的卖点。
8. 不要从关键词库反推材质、容量、安全、护理方式、功能、适配对象、认证、电池续航或性能。
9. 最终 pass/fail 由本地确定性检查决定，AI 文案质量不能覆盖审核结果。
10. `OPENAI_API_KEY` 只能在服务端使用，不能暴露到前端。

## 输出顺序

Listing 生成必须按以下顺序输出：

1. Title
2. Item Highlights
3. Bullet Points
4. Product Description
5. Search Terms
6. Search Terms bytes
7. Keyword embedding summary
8. Blocked input / risk screening
9. Forbidden-term check
10. CDQ consistency check
11. Needs manual confirmation

## 输出硬标准

- Title：英文最多 75 字符，尽量 70-75 字符，最多 1 个英文逗号，必须以准确品牌名开头。
- Item Highlights：115-125 英文字符。
- Bullet Points：必须正好 5 条。
- Product Description：默认 1800-2000 英文字符，除非用户要求更短。
- Search Terms：小于 250 UTF-8 bytes，小写，空格分隔，无逗号，无品牌名，无竞品名，无 ASIN，无风险词，无重复 root。
- 面向客户的输出中，禁用词 / 高危词命中必须是 0。

## 类目数据约定

统一使用：

`amazon-listing-webapp/data/categoryKeywordData.json`

当前应包含这些 key：

- `rug`
- `chair`
- `pet_water_fountain`

每个类目对象应包含：

- `categories`：分组关键词池。
- `keywordLibrary`：关键词行，通常包含 `term`、可选 `aba`、可选点击 / 转化 share 字段。
- `forbiddenTerms`：用于确定性筛查的风险词 / 禁用词。
- 可选 `label`、`sourceFiles` 等元数据。

不要把 JSON 词库复制到 `agents/`。`agents/` 只放规则说明，真正词库以 app 数据文件为准。

## 改代码时的边界

如果要改实现，必须保留：

- `lib/categoryKeywordRouting.ts` 的类目路由机制。
- `lib/audit.ts` 的服务端 CDQ 审核逻辑。
- Search Terms 字节计算和 root 去重。
- 生成前和生成后的风险词过滤。
- 关键词绿色高亮逻辑：模型只返回普通关键词，前端负责包 `<span className="keyword-hit">...</span>`。
- API 额度、计费或模型失败时，本地 SOP 生成兜底。
- 文案可读性优先，不能只为了埋词牺牲正常表达。

## 验证方式

如果改了代码，优先跑：

```bash
cd amazon-listing-webapp
npm run build
```

如果只改 AGENTS / Markdown 文档，检查文件存在、路径正确、关键规则没有丢即可。
