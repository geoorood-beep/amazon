# Rug 历史数据：结构与入库

## 目录和命名

- `raw/`：用户原始文件，不改字段、不覆盖；
- `normalized/`：标准化结果；
- `reference/category-history/rug/metadata.md`：来源、时间、证据粒度和边界。

原始文件命名用 `raw/YYYYMMDD_类目_来源_报表.xlsx`；标准化文件用 `normalized/YYYYMMDD_rug_historical_performance_normalized.xlsx`。多账号或产品线必须在文件名和 metadata 中区分。

## 证据粒度

| 证据 | `evidence_grain` | 可证明 |
|---|---|---|
| Amazon Customer Search Term Report | `CUSTOMER_SEARCH_TERM` | 买家实际查询，但仍要保留 Campaign/Target 映射 |
| 关键词/投放对象分析汇总 | `TARGETING_KEYWORD` | 投放词效果，不能证明真实买家查询 |

当前固定文件是第二种。legacy `search_term` 列只是历史命名，读取时必须解释为 `TARGETING_KEYWORD`。

## 标准字段

| 分组 | 字段 |
|---|---|
| 范围 | `category`、`subcategory`、`source_product`、`source_asin`、`source_sku` |
| 时间 | `date_start`、`date_end` |
| 证据 | `evidence_grain`、`historical_performance_keyword` 或经证实的 `customer_search_term` |
| 对象 | `campaign`、`ad_group`、`match_type`、`targeting` |
| 指标 | `clicks`、`spend`、`ad_orders`、`sales`、`acos`、`cvr`、`cpa`、`currency` |
| 追溯 | `source_file`、`source_sha256`、`data_confidence`、`notes` |

字段不足时留空并写缺失，不得补造。没有订单字段的文件只是观察数据，不得标记为历史成交证据。

## 有效性和入库

1. 确认为 Rug；类目不明进待确认；
2. 记录日期范围；无日期不得判断近期趋势；
3. 明确证据粒度，不用列名猜测；
4. 指标转为数值并保留原始行；
5. 可建聚合表，但 raw 不得删除；
6. 记录数据置信度、缺失字段、原文件和 SHA-256；
7. 更新 `reference/category-history/rug/metadata.md` 和校验结果。

用户只是临时提供文件时不擅自入库；只有用户要求固定时才写入本项目。
