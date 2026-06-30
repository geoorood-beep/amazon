# Walmart Knowledge Base 表格契约

Walmart Listing 的 source of truth 是当前类目的 workbook。不要依赖记忆、旧输出或手工保存的关键词片段。

## 每个类目应有的目录

建议：

```text
category_libraries/<category>/
  walmart_listing_knowledge_base.xlsx
  rules.md
```

`rules.md` 可选，用于保存该类目的补充规则；平台通用规则仍以 `agents/walmart/` 为准。

## Workbook 必需内容

每个类目的 workbook 至少要提供：

1. 关键词表
   - query / keyword
   - Frequency Rank
   - conditional note / 使用条件
   - 可选 priority 标记，如红字 / 橙字 / core / priority
2. 文案规则表
   - 平台规则
   - 类目规则
   - title / description / key feature 结构要求
3. 违禁词 / 风险词表
   - term
   - translation 或 variant
   - category
   - reason / note
   - action，例如 BLOCK / CAUTION

当前 rug skill 使用的 sheet 名是：

- `关键词（5月数据）`
- `沃尔玛文案规则`
- `沃尔玛违禁词汇总`

未来新增类目可以沿用这三个 sheet 名，减少脚本改动。

## prepare 输出要求

`prepare` 生成的 context JSON 必须包含：

- `knowledge_status.ready`：必须为 `true`。
- keyword count：非 0。
- Frequency Rank count：非 0。
- conditional-note count：非 0，除非该类目明确不需要条件规则。
- prohibited-term count：非 0。
- `input_scan.pass`：必须为 `true`。
- `selected_keywords`：当前产品可用候选词。
- `generation_rules`：当前类目输出规则。
- 类目特有 decision，例如 rug 的 size decisions。

如果任何核心数据缺失，停止生成并报告缺失项。

## 关键词选择规则

- 先风险扫描，再看条件规则，再看相关性，再看 Frequency Rank。
- 公式默认：`total_score = fr_score * 0.40 + relevance_score * 0.60`。
- Frequency Rank 不能拯救不相关或证据不支持的词。
- Workbook 中标红 / 标橙词是优先候选，不是强制使用词。
- 覆盖率只按有效 unique roots 计算。
- 被风险扫描、条件规则或证据规则排除的词，不能计入覆盖率。

## 类目条件规则

不同类目必须有自己的条件规则。例如：

- Rug：runner 词必须有 runner size 或 runner 证据。
- Chair：big and tall、ergonomic、lumbar、massage、footrest 必须有确认属性。
- Pet water fountain：stainless steel、wireless、battery、filter、sensor、quiet、runtime 必须有确认属性。

这些条件应写进 workbook notes 或类目 rules，不要藏在自由文案里。
