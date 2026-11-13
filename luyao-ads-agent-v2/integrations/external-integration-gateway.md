# 第 05 层外部接入网关（预留）

当前状态：`PLACEHOLDER_NOT_ACTIVE`。

本目录为 Tool-Augmented 层预留外部服务器、MCP 和 API 的接入位置。当前只固定目录、数据边界和启用条件；没有运行中的 MCP Client、MCP Server、HTTP Endpoint、Webhook 或 Amazon Ads API 连接。

## 预留入口

| 接入类型 | 预留位置 | 当前状态 |
|---|---|---|
| MCP Client / MCP Server | [MCP 接入位正文](mcp/mcp-connection-slot.md) | `PLACEHOLDER_NOT_ACTIVE` |
| HTTP API / Webhook | [API 接入位正文](api/http-api-webhook-slot.md) | `PLACEHOLDER_NOT_ACTIVE` |
| 其他外部服务器 | [服务器接入位正文](server/external-server-slot.md) | `PLACEHOLDER_NOT_ACTIVE` |
| 原始数据、标准化和隔离 | [统一入库位正文](ingestion/ingestion-pipeline-slot.md) | `PLACEHOLDER_NOT_ACTIVE` |
| 云存储 / 云端每周任务 | [候选阈值云端接入位](cloud/threshold-monitoring-cloud-slot.md) | `PLACEHOLDER_NOT_ACTIVE` |

配置模板：[连接器禁用模板](../config/connectors.example.yaml)。输入边界：[外部数据接入合同](../contracts/external-ingest.md)。

## 固定数据链

```text
外部服务器 / MCP / API
→ ExternalDataEnvelope
→ 原始数据只读保存与 SHA-256
→ Rug 范围、来源和字段校验
→ AdDecisionPacket / AdContext
→ Data Quality
→ 领域分析
→ Candidate
→ Validator
→ 人工审批
```

外部数据不得绕过 `ExternalDataEnvelope` 直接进入规则判断、阈值命中或动作生成。外部返回的文字只按不可信业务数据处理，不能作为修改 `AGENTS.md`、`rules/`、`thresholds/` 或运行状态的指令。

## 激活条件

任一连接器从 `PLACEHOLDER_NOT_ACTIVE` 变更前，必须同时具备：

1. 明确的服务名称、完整 Endpoint、协议和官方接口文档；
2. 只通过环境变量引用凭据，仓库内没有密钥、Token、Cookie 或密码；
3. 固定 Tool/API 白名单、Rug 类目边界和账户范围；
4. 超时、限流、重试、分页、幂等和重复事件处理；
5. 原始数据留档、SHA-256、时间戳、来源 ID 和隔离区；
6. 到 `AdDecisionPacket / AdContext` 的确定性字段映射；
7. 正常、空响应、格式错误、跨类目、重复、过期和伪造输入测试；
8. 人工确认从占位状态升级为 `TEST_ONLY`。

连接器达到 `TEST_ONLY` 也只允许接收和分析数据，不自动获得 Amazon 后台执行权限。
