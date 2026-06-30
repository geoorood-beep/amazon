# Walmart 风险与发布审核

Walmart Listing 只有通过 deterministic audit 才能发布。

## 规则优先级

1. 禁用词、平台政策、IP 风险、未支持声明。
2. 当前产品证据和 CDQ 一致性。
3. Workbook conditional notes。
4. 最新明确运营规则。
5. Workbook general rules。
6. 相关性。
7. Frequency Rank。
8. 文案润色。

## 风险扫描范围

必须扫描：

- 用户输入。
- OCR。
- 竞品参考。
- 候选关键词。
- Product Title。
- Description。
- Key Features。

用户提供文本不豁免。

## 证据规则

只能使用当前产品图片和当前用户属性。

不要推断：

- material
- backing
- washability
- low pile
- pet claims
- certifications
- safety
- medical
- antibacterial
- waterproof
- fireproof
- absolute performance

视觉置信度低时，颜色和风格要保守。

## Product Title 审核

- 10-199 characters。
- 目标 120-180 characters。
- Proper Capitalization。
- 品牌、尺寸、确认转化卖点、产品类型、主场景尽量放在前 70-80 characters。
- 不写促销、物流、平台、价格、排名、无关年份、URL、HTML、emoji、装饰符号、多品牌、无关产品类型。
- 不自然堆砌禁止；自然且有搜索意图的 `Rug` 重复可允许。

## Description 审核

- 英文一段。
- 80-150 words。
- 通常 4-5 句。
- 包含品牌、产品名 / 类目、确认功能、完整场景、确认结构、尺寸、护理、必要限制。
- 避免用 `it`、`its`、`this`、`these` 指代产品；重复有搜索价值的 noun phrase。
- 不使用 bullets、编号、HTML、emoji、URL、编造说明。

## Key Features 审核

- 默认 5 条，允许 3-10 条。
- 格式：`Short Benefit Title: buyer-value sentence`。
- 每条一个主卖点。
- 每条 180-280 characters。
- 后续 size variant 不能偷工减料，不能把核心卖点写得更短。

## 发布 gate

只有同时满足以下条件才可释放：

- knowledge base ready。
- input risk scan pass。
- output risk scan pass。
- 每个 title 10-199 characters。
- description 一段且 80-150 words。
- Key Features 数量和长度通过。
- title 数量等于 supplied sizes 数量。
- 类目条件规则通过。
- 当前证据支持每个 claim。
- Product Title、Description、Key Features 互相一致。

## 用户可见风险报告

不要暴露 blocked raw terms。

只报告：

- 风险类别。
- 动作，例如 BLOCK / REMOVE / NEEDS_PROOF。
- 原因。
- 需要用户补充的证据。
