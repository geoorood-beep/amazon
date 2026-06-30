# Walmart 新类目模板

新增 Walmart 类目时，复制本模板并改名为：

`agents/walmart/categories/<category>.md`

类目 key 使用小写 snake_case，例如：

- `chair`
- `pet_water_fountain`
- `dog_leash`
- `pet_feeder`

## 类目定义

- 类目 key：`<category>`
- Walmart 节点 / 货架：待填写
- 主产品名：待填写
- 支持的变体维度：尺寸 / 颜色 / 容量 / 材质 / 套装等

## Knowledge Base

准备：

```text
category_libraries/<category>/walmart_listing_knowledge_base.xlsx
category_libraries/<category>/rules.md
```

Workbook 至少包含：

- 关键词 + Frequency Rank。
- 条件使用备注。
- 平台 / 类目文案规则。
- 违禁词 / 风险词。

## 类目条件规则

填写该类目的条件约束，例如：

- 哪些关键词只能在特定尺寸 / 功能 / 材质确认后使用。
- 哪些高流量词属于配件-only，不能用于主产品。
- 哪些功能词需要证明。
- 哪些场景词只适合特定规格。

## Product Title 规则

填写：

- 标题长度目标。
- 品牌 / 尺寸 / 核心产品词 / 功能词 / 场景词顺序。
- 必须放在前 70-80 characters 的信息。
- 禁止使用的标题词。

## Description 规则

填写：

- 字数范围。
- 必须覆盖的产品事实。
- 禁止的表达。
- 推荐 noun phrase。

## Key Features 规则

填写：

- feature 数量。
- 每条字符范围。
- 必须覆盖的卖点。
- 需证明项。

## Release Gate

填写该类目发布前必须通过的检查。

默认继承：

- knowledge base ready。
- input / output risk scan pass。
- 当前证据支持每个 claim。
- Product Title、Description、Key Features 一致。
- `release_status = PASS` 才能交付。
