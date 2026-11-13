# Walmart Listing 智能体

本目录是 Walmart US Listing 的 AGENTS 规则。它来自 `$walmart-listing-generator` skill，但改造成多类目架构：后续只要接入不同品类的关键词表 / 风险表 / 条件规则表，就能按同一流程生成不同类目的 Walmart Listing。

## 必读顺序

处理 Walmart / 沃尔玛 Listing 任务时，按顺序读取：

1. `AGENTS.md`
2. `agents/walmart/index.md`
3. `agents/walmart/category-routing.md`
4. `agents/walmart/knowledge-base-contract.md`
5. `agents/walmart/generation-workflow.md`
6. `agents/walmart/risk-audit.md`
7. 对应类目文件：
   - `agents/walmart/categories/rug.md`
   - 新类目参考 `agents/walmart/categories/new-category-template.md`

## 平台边界

Walmart Listing 不使用 Amazon Listing 的输出结构。

Walmart 输出模块是：

- Product Title，每个 size 一个 title。
- Description，一段英文描述。
- Key Features，默认 5 条，允许 3-10 条。

Walmart 不输出 Amazon 的：

- Bullet Points
- Search Terms
- Search Terms bytes
- Amazon CDQ 表达

## 目标架构

Walmart 多类目架构应是：

```text
walmart-runtime/
  scripts/
    walmart_kb.py
  category_libraries/
    rug/
      walmart_listing_knowledge_base.xlsx
      rules.md
    chair/
      walmart_listing_knowledge_base.xlsx
      rules.md
    pet_water_fountain/
      walmart_listing_knowledge_base.xlsx
      rules.md
  runs/
    <run-id>/
      current_product.txt
      walmart_context.json
      draft.json
      walmart_audit.json
```

当前 skill 的脚本是单 workbook 版本，默认读取：

`assets/walmart_listing_knowledge_base.xlsx`

未来改成多类目时，应增加 `--category` 或 `--workbook` 参数，让 prepare / scan / audit 都加载当前类目的完整 workbook。

## 基本流程

1. 只收集当前产品事实，不继承上一轮产品信息。
2. 把当前产品属性、卖点、OCR、竞品参考写入 UTF-8 临时文本。
3. 按类目加载 Walmart knowledge base。
4. 运行 prepare，拿到 `selected_keywords`、风险扫描结果、size decisions。
5. 只用 `selected_keywords` 作为候选关键词池。
6. 生成 draft JSON。
7. 运行 audit。
8. 只有 `release_status` 为 `PASS` 才输出最终 Listing。

## 硬规则

- 每次 prepare / scan / audit 都必须加载并验证完整 workbook。
- 用户提供的文本也必须做 prohibited-term scanning。
- Workbook notes 优先于 Frequency Rank。
- 相关性优先于流量。
- 被脚本排除的关键词，不能手工加回草稿；除非重新 prepare。
- 禁止在用户可见审核中暴露 blocked raw terms，只报告风险类别、处理动作和原因。
