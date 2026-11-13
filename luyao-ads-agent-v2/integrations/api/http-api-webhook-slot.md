# HTTP API 与 Webhook 接入位（预留）

当前状态：`PLACEHOLDER_NOT_ACTIVE`。

本目录预留：

- 主动轮询外部 REST API；
- 接收外部系统推送的 Webhook；
- 提供只读的分析请求和批次状态接口。

当前没有 HTTP Server、路由、监听端口或公网 Endpoint。文档中的未来接口名称不代表已经启用。

## 未来接口边界

建议只预留以下职责：

```text
POST /v1/ingest       接收 ExternalDataEnvelope
POST /v1/analyze      对已冻结 snapshot 发起分析
GET  /v1/batches/:id  查询接收、校验和分析状态
GET  /health          查询服务健康状态
```

必须实现认证、签名校验、时钟偏差、Body 大小限制、Content-Type 白名单、幂等键、速率限制、超时、错误码和审计日志。任何接口均不得直接修改 Amazon 广告。
