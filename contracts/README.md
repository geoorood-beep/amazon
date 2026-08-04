# 数据与输出合同

当前规则版本：`V2.0`

合同定义“必须有哪些字段和状态”，不决定业务阈值。

| 文件 | 内容 |
|---|---|
| [数据输入](data-input.md) | AdContext、数据快照、报表和对象映射 |
| [动作与方案](action-and-plan.md) | 候选动作、最终方案和执行确认 |
| [广告架构设计输出](new-product-output.md) | Rug 广告架构两张核心表的必备字段 |
| [新品匹配证据](new-product-match-evidence.md) | ASIN相关性表、搜索词月搜索量表和去重键 |
| [SP广告优化输出](old-product-output.md) | SP完整/有限模式的可见字段 |
| [复盘合同](review.md) | 复盘资格、证据和 CANDIDATE 输出 |
| [广告报表聚合](ad-report-aggregation.md) | 六表输入、标准化粒度、聚合工作簿和数据质量状态 |
| [外部数据接入](external-ingest.md) | 第 05 层 MCP/API/服务器输入信封与隔离边界；当前仅占位 |
| [历史阈值校准](threshold-calibration.md) | 日粒度累积、候选包、时间留出证据和人工批准字段 |
| [本地运营任务](operator-job.md) | 四个网页入口、任务状态、Codex Worker 与 Validator 安全边界 |
| `../ai_ads/schemas/` | 机器可读 JSON Schema |

机器 Schema 与本目录语义不一致时必须阻断并修复，不得由模型猜测哪一份正确。
