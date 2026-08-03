# 陆遥广告智能体 V2.0 — 八层总入口

本文件只负责最高优先级边界和路由。当前规则正文位于 [rules/](rules/README.md)，数值位于 [thresholds/](thresholds/README.md)，输入输出字段位于 [contracts/](contracts/README.md)，数据源位于 [knowledge/](knowledge/README.md)。第 05 层外部工具接入位于 [外部接入网关正文](integrations/external-integration-gateway.md)，当前全部为占位状态。不要把具体规则或阈值重新堆回本文件。

当前状态：`V2.0_FROZEN`；`HUMAN_EXECUTION_ONLY`；`ai_ads/` 为 `TEST_ONLY`；Amazon 后台自动执行关闭。冻结文件清单见 [V2.0 Release](releases/v2.0/RELEASE.md)。

## 最高优先级边界

1. 每次任务先读取 `config/project_scope.json`。
2. 唯一允许类目是 `rug`；禁止读取或引用宠物喂水器、办公椅及其他项目数据或阈值。
3. 非 Rug 任务立即停止，并提示切换到 `/Users/leo/Documents/有它广告智能体`。
4. 固定数据只允许读取白名单路径；用户本次新数据仍需做类目和证据粒度检查。
5. 未确认的阈值不得补造；圆形 Rug 性能阈值和机器低样本强收缩权限仍阻断。
6. `AUTO_PASS` 只表示 Validator 通过，不表示已经执行或允许自动执行。

## 八层读取顺序

1. [ReAct 路由](architecture/layers/01-react-router.md)
2. [Plan-and-Execute](architecture/layers/02-plan-execute.md)
3. [领域协作](architecture/layers/03-domain-agents.md)
4. [Validator / 复盘](architecture/layers/04-reflective-validator.md)
5. [工具层](architecture/layers/05-tool-augmented.md)
6. [状态与记忆](architecture/layers/06-memory-state.md)
7. [知识检索](architecture/layers/07-rag-knowledge.md)
8. [受控闭环](architecture/layers/08-autonomous-loop.md)

架构总览：[八层架构导航](architecture/README.md)。

## 任务路由

| 任务 | 规则入口 | 阈值入口 |
|---|---|---|
| Rug 类目 / 尺寸 | [Rug 类目规则](rules/domains/rug-category.md) | [尺寸路由](thresholds/rug/size-routing.md) |
| 新品选词 / 新广告 | [输入](rules/domains/new-product/scope-input-sources.md)、[属性选词](rules/domains/new-product/attribute-and-selection.md)、[架构](rules/domains/new-product/architecture.md)、[隔离](rules/domains/new-product/negative-isolation.md) | [新品阶段](thresholds/rug/new-product-stage.md)、[预算与隔离](thresholds/rug/budget-and-isolation.md) |
| 老品优化 | [输入模式](rules/domains/old-product/input-and-modes.md)、[诊断](rules/domains/old-product/diagnosis.md)、[预算/Bid/广告位](rules/domains/old-product/budget-bid-placement.md)、[趋势](rules/domains/old-product/product-and-trend.md)、[拓量](rules/domains/old-product/growth-and-structure.md) | [性能阈值](thresholds/rug/performance.md)、[治理阈值](thresholds/rug/governance.md) |
| 搜索词 / 词根 | [语义聚合](rules/domains/search-term/semantic-aggregation.md)、[评分与动作](rules/domains/search-term/scoring-and-actions.md) | [评分与拓量门](thresholds/rug/traffic-and-scoring.md) |
| 类目流量 | [输入](rules/domains/category-traffic/scope-and-input.md)、[分层](rules/domains/category-traffic/relevance-and-segmentation.md)、[打法](rules/domains/category-traffic/structure-and-playbook.md)、[输出](rules/domains/category-traffic/output-and-confidence.md) | [流量结构阈值](thresholds/rug/traffic-and-scoring.md) |
| 历史效果数据 | [字段与入库](rules/domains/history-data/schema-and-ingest.md)、[使用边界](rules/domains/history-data/usage-boundaries.md) | 不适用 |
| 外部服务器 / MCP / API | [第 05 层接入占位](integrations/external-integration-gateway.md)、[外部数据接入合同](contracts/external-ingest.md) | 不适用；当前 `PLACEHOLDER_NOT_ACTIVE` |
| 输出表格 | [输出规则正文](rules/output/output-rules.md) | 按主任务引用 |
| 动作 / Validator | [动作仲裁规则](rules/core/action-arbitration-validator.md) | 按动作引用 |

核心安全规则统一从 [rules/core/](rules/README.md) 读取。字段合同统一从 [contracts/](contracts/README.md) 读取。数据来源统一从 [knowledge/](knowledge/README.md) 读取。

## AGENTS 目录命令

当用户输入 `AGENTS 目录` 时，读取并展示 [可点击 AGENTS 目录](agents/agents-directory.md)。必须说明：模块结果、用户输入、维护数据和缺失影响。

新增、删除、改名或调整模块时，必须同步更新：

- `agents/agents-directory.md`；
- 对应目录 README；
- `config/project_scope.json`；
- 相关校验器。

## 单一真源

- 判断逻辑：`rules/`；
- 数值和区间：`thresholds/`；
- 字段和状态：`contracts/`；
- 数据来源：`knowledge/`；
- 外部连接器：`integrations/`，只负责接收和标准化，不得保存业务规则或阈值；
- 八层职责：`architecture/`；
- 旧版本：`history/`，仅追溯；
- 旧 `agents/*.md`：只做兼容路由。

同一数值不得同时维护在规则和阈值文件。规则引用数值时只写阈值文件或 Threshold ID。

## V2.0 状态边界

- 架构来源：[AI广告Agent完整架构与实施方案 V2.0](docs/v2/source/AI广告Agent完整架构与实施方案_V2.0.md)；SHA-256 在 [项目边界配置](config/project_scope.json)。
- 规则包必须分别保存规则文件和阈值文件 SHA-256。
- `SP_STANDARD_OPTIMIZATION` 只做 TEST_ONLY 结构验证；`SP_COLD_START` 为 `CAPABILITY_NOT_ACTIVE`；SB/SD 不支持。
- 复盘只能生成证据和 CANDIDATE，不能覆盖 ACTIVE。
- 当前没有生产机器 ACTIVE 规则包。
- MCP、HTTP API、Webhook 和其他外部服务器连接器当前均为 `PLACEHOLDER_NOT_ACTIVE`；预留目录不代表已经连接或允许执行。

## 每次交付前

运行：

```bash
.venv/bin/python scripts/validate_project_scope.py
.venv/bin/python scripts/validate_v20_rules.py
.venv/bin/python scripts/validate_phase1_decisions.py
.venv/bin/python scripts/validate_integration_placeholders.py
.venv/bin/python -m pytest new_product_module/tests ai_ads/tests -q
.venv/bin/python scripts/stress_test_v20.py
.venv/bin/python scripts/v20_release_manifest.py
```

任一校验失败，不得宣称规则、阈值或智能体已完成。
