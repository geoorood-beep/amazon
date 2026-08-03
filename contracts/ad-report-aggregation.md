# 合同：广告报表聚合

## 输入

- 输入目录：同一账户、同一链接、同一观察周期的六类 SP 报表；
- 批次上下文：`category`、Marketplace、Account ID、Link ID、时区、币种、归因窗口和周期；
- 可选人工映射：标准 `report_id` 到具体文件路径；
- 支持格式：`.csv`、`.tsv`、`.xlsx`。

标准 `report_id`、必需字段、可选字段和表头别名统一维护在 [聚合配置](../config/ad_report_aggregation.json)。

## 输出

### `ad_decision_packet.json`

必须符合 `ai_ads/schemas/ad-decision-packet.schema.json`，并包含：

- Data Snapshot 元数据；
- 六类源报表的文件名、工作表、周期、有效行数和 SHA-256；
- Campaign、Ad Group、Target、搜索词父级链；
- Campaign、Ad Group、Target、搜索词的 D3 / D7 / D14 / D30 指标；
- Placement 和 Advertised Product 的观察周期 `CUSTOM` 指标；
- 导入问题和对账状态。

### `ad_decision_packet.xlsx`

必须包含：

| Sheet | 作用 |
|---|---|
| `00_SNAPSHOT` | 数据质量、周期、30日总量和趋势 |
| `01_AGENT_INPUT` | 智能体唯一聚合输入表 |
| `02_RECONCILIATION` | 搜索词每日明细与汇总对账 |
| `03_EVIDENCE_INDEX` | 源文件、行数、周期和 SHA-256 |
| `04_CAMPAIGNS` | Campaign 结构事实 |
| `05_AD_GROUPS` | Ad Group 结构事实 |
| `06_TARGETS` | Target / Keyword 结构事实 |
| `07_SEARCH_TERMS` | 搜索词父级链事实 |
| `08_ISSUES` | BLOCK / APPROVAL 问题 |
| `09_DAILY_TOTALS` | 搜索词每日明细的账户趋势 |

`CTR / CVR / CPC / CPA / ACOS / ROAS` 在工作簿中使用公式计算；JSON 保留合同要求的原始可加指标，避免把显示公式结果误当新证据。

## 粒度和禁止项

1. `SEARCH_TERM`、`TARGET`、`AD_GROUP`、`CAMPAIGN`、`PLACEMENT` 和 `ADVERTISED_PRODUCT` 是不同粒度；不得跨粒度直接相加。
2. 账户 30 日总量只从 `SP搜索词-按词-每日明细` 汇总一次。
3. 汇总搜索词只用于对账，不再次计入账户总量。
4. 源报表保持原样；聚合结果通过证据索引追溯，不改写源文件。
5. 聚合工具不得写入广告动作、ACTIVE 阈值命中、`AUTO_PASS` 执行权限或 Amazon API 调用。

## 数据质量状态

- `DQ_PASS`：六表、父级链、周期、漏斗和对账均通过；
- `DQ_WARNING`：没有 BLOCK，但存在需要人工确认的问题；
- `DQ_BLOCKED`：任一必需条件失败，不得进入广告判断。

金额 `0.01 币种单位` 只作为同一搜索词每日明细与汇总的技术舍入容差，不是业务阈值。
