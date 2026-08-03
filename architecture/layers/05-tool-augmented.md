# 第 05 层：Tool-Augmented 工具层

## 工具职责

- 读取并标准化报表；
- 计算确定性指标；
- 校验文件、字段、公式、SHA-256 和 Schema；
- 生成结构化候选表；
- 运行回归测试。

## 工具边界

工具不得自行决定：

- 样本是否足够；
- 业务状态是否优质或高风险；
- 应该加减预算、Bid、广告位或暂停；
- 未确认阈值应填什么数。

主要入口：

- `new_product_module/`：新品人工架构辅助；
- `ai_ads/`：V2 `TEST_ONLY` 合同、仲裁和 Validator；
- `scripts/`：数据导入与项目校验；
- `contracts/README.md`：工具必须遵守的字段合同。

## 外部接入网关预留

第 05 层已为外部服务器、MCP 和 API 预留统一入口：[外部接入网关正文](../../integrations/external-integration-gateway.md)。当前状态固定为 `PLACEHOLDER_NOT_ACTIVE`，没有运行中的 Endpoint 或连接器。

| 接入类型 | 预留正文 | 当前权限 |
|---|---|---|
| MCP Client / MCP Server | [MCP 接入位正文](../../integrations/mcp/mcp-connection-slot.md) | 不可连接 |
| HTTP API / Webhook | [API 接入位正文](../../integrations/api/http-api-webhook-slot.md) | 不可监听、不可调用 |
| 其他外部服务器 | [服务器接入位正文](../../integrations/server/external-server-slot.md) | 不可连接 |
| 统一入库和隔离 | [入库接入位正文](../../integrations/ingestion/ingestion-pipeline-slot.md) | 不创建生产批次 |

所有未来连接器必须先生成 [ExternalDataEnvelope](../../contracts/external-ingest.md)，保存原始输入和 SHA-256，再转换为 `AdDecisionPacket / AdContext`。外部输入不得直接携带 `DQ_PASS`、`AUTO_PASS`、`ACTIVE` 或广告动作权限。

占位配置见 [connectors.example.yaml](../../config/connectors.example.yaml)。修改占位状态前必须运行 `scripts/validate_integration_placeholders.py` 并新增真实连接器测试。
