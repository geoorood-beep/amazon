# 合同：外部数据接入（预留）

当前状态：`PLACEHOLDER_NOT_ACTIVE / DOCUMENTATION_ONLY`。

本合同为第 05 层外部接入网关预留 `ExternalDataEnvelope`。当前没有对应的运行服务或生产 Schema；不得因为本文存在就宣称 MCP/API 已接通。

## ExternalDataEnvelope 最低字段

- `schema_version`；
- `connector_id`、`connector_type`、`connector_version`；
- `external_event_id` 和项目内部 `trace_id`；
- `received_at`、`source_generated_at`，均带明确时区；
- `marketplace`、`account_id`、`link_id`、`category`；
- `payload_format`、`content_type`、`content_length`；
- `content_sha256` 和原始数据只读位置；
- `report_type`、`period_start`、`period_end`、`row_count`；
- `source_object_id`、`source_version` 或 ETag；
- `normalization_status`、`quarantine_reason`；
- `idempotency_key`。

`category` 必须为 `rug`。未知、为空或非 Rug 时直接隔离。

## 转换边界

```text
ExternalDataEnvelope
→ 来源与完整性校验
→ 报表字段标准化
→ AdDecisionPacket + AdContext
→ Data Quality
```

外部系统不得提前写入以下结论：

- `DQ_PASS`；
- `AUTO_PASS`；
- `ACTIVE` Rule/Threshold；
- 整体状态；
- Bid、预算、Placement、暂停或否词动作。

这些状态必须由本项目的当前规则、阈值和 Validator 重新计算。

## 失败处理

缺字段、SHA-256 不一致、事件重复、时间过期、父级链不完整、账户越界或来源身份无法确认时固定进入 `quarantine`，不得降级为可信的有限模式数据。
