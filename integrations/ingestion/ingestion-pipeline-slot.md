# 外部数据统一入库位（预留）

当前状态：`PLACEHOLDER_NOT_ACTIVE`。

所有 MCP、API 和外部服务器连接器未来必须共用本层，不能各自绕过数据质量门。

## 预留职责

```text
raw/          原始响应或文件，只读保存
normalized/   转换后的 ExternalDataEnvelope 和业务对象
quarantine/   越界、无效、重复、过期或无法解析的数据
manifests/    批次来源、SHA-256、行数和转换记录
```

这些运行目录当前不创建、不纳入冻结包。正式实现时必须放在项目允许的运行数据根目录，并加入版本控制忽略规则。

## 固定处理顺序

1. 先保存原始输入并计算 SHA-256；
2. 校验连接器、事件 ID、时间、类别和账户范围；
3. 使用 `connector_id + external_event_id + content_sha256` 做幂等判定；
4. 转换为 [外部数据接入合同](../../contracts/external-ingest.md)；
5. 再构建 `AdDecisionPacket / AdContext`；
6. Data Quality 未通过时进入隔离区；
7. 只有通过数据质量门的数据才能交给领域分析。
