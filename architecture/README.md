# 陆遥广告智能体八层架构

当前规则版本：`V2.0`

这套八层结构参考用户提供的 ReAct、Plan-and-Execute、Multi-Agent、Reflective、Tool-Augmented、Memory-Augmented、RAG 和 Autonomous Loop 八种能力，但按本项目实际职责重新落盘。它们是职责层，不是八个都可以独立改规则的 Agent。

## 八层导航

| 层 | 能力 | 本项目职责 | 人工主要维护 |
|---|---|---|---|
| [01 ReAct](layers/01-react-router.md) | ReAct | 接收任务、检查 Rug 边界、选择任务类型和读取路径 | 路由和能力边界 |
| [02 Plan-and-Execute](layers/02-plan-execute.md) | Plan-and-Execute | 把分析、候选动作、Validator、人工执行分开 | 阶段门和执行顺序 |
| [03 Multi-Agent](layers/03-domain-agents.md) | Multi-Agent | 新品、老品、搜索词、流量结构、历史数据模块分工 | 各领域规则，不在总入口堆规则 |
| [04 Reflective](layers/04-reflective-validator.md) | Reflective Agent | 独立 Validator、执行确认、复盘、CANDIDATE 隔离 | Validator 与复盘资格 |
| [05 Tool-Augmented](layers/05-tool-augmented.md) | Tool-Augmented | 已启用本地六表聚合；并保留 Schema、脚本和外部接入网关占位 | 工具输入输出合同与连接器状态 |
| [06 Memory-Augmented](layers/06-memory-state.md) | Memory-Augmented | 保存批次、快照、执行结果和规则证据 | 正式记忆，不用聊天记忆代替证据 |
| [07 RAG](layers/07-rag-knowledge.md) | RAG Agent | 按白名单检索 ABA、历史效果、阈值和当前报表 | 数据源优先级与证据粒度 |
| [08 Autonomous Loop](layers/08-autonomous-loop.md) | Autonomous Loop | 受控闭环、能力启用门、人工审批和停止条件 | 生产启用门；当前仍禁止自动执行 |

从上表可直接进入每一层。业务维护还可直达[规则目录](../rules/README.md)、[阈值目录](../thresholds/README.md)、[数据源](../knowledge/README.md)、[字段合同](../contracts/README.md)和[外部接入网关正文](../integrations/external-integration-gateway.md)。

## 文件职责

| 目录 | 只能保存什么 | 不允许保存什么 |
|---|---|---|
| [rules/](../rules/README.md) | 条件、判断顺序、权限、动作关系 | 可调整数值、历史版本全文 |
| [thresholds/](../thresholds/README.md) | 数值、区间、单位、Threshold ID、确认状态 | 决策流程和长篇操作说明 |
| [contracts/](../contracts/README.md) | 输入输出字段、枚举、状态、Schema 说明 | 业务阈值 |
| [knowledge/](../knowledge/README.md) | 数据源、证据粒度、读取优先级 | 广告动作规则 |
| [integrations/](../integrations/external-integration-gateway.md) | MCP、API、服务器连接器和统一入库的技术边界 | 业务规则、阈值、密钥和自动执行权限 |
| [architecture/](README.md) | 分层职责和读取顺序 | 具体阈值 |
| [history/](../history/README.md) | 已冻结旧版本和校验值 | 当前有效规则 |
| [agents/](../agents/agents-directory.md) | 旧路径兼容入口和人工导航 | 新增完整规则正文 |

## 单一真源规则

1. 同一个可调整数值只能在 `thresholds/` 出现一次；其他文件只引用 Threshold ID 或文件路径。
2. 同一个判断逻辑只能在 `rules/` 有一个当前正文；`agents/` 只做兼容路由。
3. `history/` 永远不参与当前规则解析。
4. `docs/v2/source/` 是架构来源，不是自动生效的规则包。
5. 代码实现必须引用机器配置或合同，不能从多个 Markdown 猜测哪个版本有效。
6. 更新规则、阈值、合同或知识源后，必须同步更新对应 README/manifest 并运行校验。
7. `integrations/` 的外部输入只能转换为数据快照，不得改写规则、阈值或运行状态。

## 推荐人工维护顺序

```text
先改 thresholds/ 中的数值或状态
→ 再检查 rules/ 是否仍引用正确的 Threshold ID
→ 再检查 contracts/ 字段是否足够
→ 运行 scripts/validate_project_scope.py
→ 运行 scripts/validate_v20_rules.py
→ 运行 scripts/validate_integration_placeholders.py
→ 运行 pytest
→ 人工批准后才允许改变运行状态
```
