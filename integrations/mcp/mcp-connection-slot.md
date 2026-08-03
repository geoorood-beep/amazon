# MCP 接入位（预留）

当前状态：`PLACEHOLDER_NOT_ACTIVE`。

本目录预留两种互不混淆的能力：

1. 本项目作为 MCP Client，调用外部 MCP Server 获取数据；
2. 本项目作为 MCP Server，向已授权客户端暴露只读分析工具。

当前两种能力均未实现、未配置、未启动。

## 未来实现前必须提供

- 服务名称和完整 MCP Endpoint；
- Transport 类型和官方工具 Schema；
- 允许调用的 Tool 白名单；
- 认证环境变量名称，不接收仓库内明文 Token；
- 超时、分页、限流、重试和撤销策略；
- 至少一份脱敏成功响应和错误响应样本；
- Tool 返回值到 `ExternalDataEnvelope` 的确定性映射。

只有 API Key、没有服务身份或 Endpoint 时不得创建连接。MCP Tool 返回的文字不得被当作系统指令或规则更新。
