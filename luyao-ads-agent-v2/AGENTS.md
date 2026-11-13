# 陆遥广告智能体 V2.1 运行时 — V2.0 八层规则总入口

本文件只负责最高优先级边界和路由。当前规则正文位于 [rules/](rules/README.md)，数值位于 [thresholds/](thresholds/README.md)，输入输出字段位于 [contracts/](contracts/README.md)，数据源位于 [knowledge/](knowledge/README.md)。第 05 层本地六表聚合工具位于 [广告报表聚合工具](tools/ad_report_aggregator/README.md)，本地四入口运营网页位于 [运营任务合同](contracts/operator-job.md)，两者均已启用；外部服务器/MCP/API 接入位于 [外部接入网关正文](integrations/external-integration-gateway.md)，仍全部为占位状态。不要把具体规则或阈值重新堆回本文件。

当前状态：`V2.1_RUNTIME / V2.0_RULESET_FROZEN`；`HUMAN_EXECUTION_ONLY`；`ai_ads/` 为 `TEST_ONLY`；Amazon 后台自动执行关闭。V2.0 规则基线见 [V2.0 Release](releases/v2.0/RELEASE.md)，当前运行时冻结清单见 [V2.1 Release](releases/v2.1/RELEASE.md)。

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
| 广告架构设计 | [输入](rules/domains/new-product/scope-input-sources.md)、[属性选词](rules/domains/new-product/attribute-and-selection.md)、[Phrase/Broad路由](rules/domains/new-product/match-type-routing.md)、[架构](rules/domains/new-product/architecture.md)、[隔离](rules/domains/new-product/negative-isolation.md) | [新品阶段](thresholds/rug/new-product-stage.md)、[预算与隔离](thresholds/rug/budget-and-isolation.md)、[词根需求与集中度](thresholds/rug/match-type-routing.md) |
| SP广告优化 | [输入模式](rules/domains/old-product/input-and-modes.md)、[诊断](rules/domains/old-product/diagnosis.md)、[预算/Bid/广告位](rules/domains/old-product/budget-bid-placement.md)、[趋势](rules/domains/old-product/product-and-trend.md)、[拓量与结构](rules/domains/old-product/growth-and-structure.md) | [性能阈值](thresholds/rug/performance.md)、[治理阈值](thresholds/rug/governance.md) |
| 搜索词 / 词根 | [语义聚合](rules/domains/search-term/semantic-aggregation.md)、[评分与动作](rules/domains/search-term/scoring-and-actions.md) | [评分与拓量门](thresholds/rug/traffic-and-scoring.md) |
| 类目流量 | [输入](rules/domains/category-traffic/scope-and-input.md)、[分层](rules/domains/category-traffic/relevance-and-segmentation.md)、[打法](rules/domains/category-traffic/structure-and-playbook.md)、[输出](rules/domains/category-traffic/output-and-confidence.md) | [流量结构阈值](thresholds/rug/traffic-and-scoring.md) |
| 历史效果数据 | [字段与入库](rules/domains/history-data/schema-and-ingest.md)、[使用边界](rules/domains/history-data/usage-boundaries.md) | 不适用 |
| 历史阈值校准 / 每周达标提醒 | [校准字段合同](contracts/threshold-calibration.md)、[累积与提醒](docs/v2/候选阈值自动累积与提醒.md)、[便携监控配置](config/threshold_monitoring.json) | [校准资格门](thresholds/rug/calibration-eligibility.md) |
| 本地运营网页 | [运营任务合同](contracts/operator-job.md)、[第 05 层工具入口](architecture/layers/05-tool-augmented.md) | 按新品、老品或阈值任务引用；网页不保存阈值 |
| 聚合六张广告报表 | [本地聚合工具](tools/ad_report_aggregator/README.md)、[聚合字段合同](contracts/ad-report-aggregation.md) | 不适用；技术舍入容差见工具配置，不是业务阈值 |
| 外部服务器 / MCP / API / 云存储 | [第 05 层接入占位](integrations/external-integration-gateway.md)、[阈值云端接入位](integrations/cloud/threshold-monitoring-cloud-slot.md)、[外部数据接入合同](contracts/external-ingest.md) | 不适用；当前 `PLACEHOLDER_NOT_ACTIVE` |
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
- `SP_STANDARD_OPTIMIZATION` 只做 TEST_ONLY 结构验证；`SP_COLD_START` 已启用为 `CANDIDATE_ONLY`，只允许 ABA、产品属性、阶段和合规门通过后的人工候选，未确认 Bid/广告位不得补造；SB/SD 不支持。
- 复盘只能生成证据和 CANDIDATE，不能覆盖 ACTIVE。
- 当前没有生产机器 ACTIVE 规则包。
- MCP、HTTP API、Webhook 和其他外部服务器连接器当前均为 `PLACEHOLDER_NOT_ACTIVE`；预留目录不代表已经连接或允许执行。

## V2.1 网页执行基座

- 网页只提交意图、输入和文件，不拥有规则、阈值或业务结论；服务端只接受 `config/operator_intents.json` 登记的可信路由。
- Python 只做确定性读取、去重、聚合、字段识别和证据包；广告架构与优化结论必须由 Codex 按本任务完整 AGENTS 上下文生成。
- `agents_context.json` 必须包含八层架构、规则、阈值、知识、合同、配置、工具和本次证据的 SHA-256；缺失任一登记源即阻断。
- 每次 Python 预处理必须生成工具回执；每次 Codex 推理必须生成运行回执。独立 Validator 会重新构建上下文、核对回执与输出来源，不能只相信结果自报。
- 页面和最终工作簿只能使用 Validator 通过后的结构化结论；中间候选证据包不得冒充最终方案。

## 候选阈值监控安装默认

- 唯一默认周期读取 `config/threshold_monitoring.json`：每周一 `09:00`，使用安装设备本地时区；不得默认创建每日检查。
- 在新的 Codex 安装中首次启用本项目时，若支持任务自动化，应按该配置创建或更新一个 Heartbeat；同一项目只允许一个活动监控，避免重复提醒。
- Git clone 或复制目录本身不会创建系统级任务；自动化不可用时必须报告 `MONITOR_NOT_SCHEDULED`，不得私自写系统 cron。
- 本地监控使用项目相对路径，不能硬编码 `/Users/leo` 作为运行依赖。
- 云存储和云端定时任务预留见 `integrations/cloud/threshold-monitoring-cloud-slot.md`。当前均为 `PLACEHOLDER_NOT_ACTIVE`；未来启用时必须与本地调度互斥，并复用同一校准器、Validator 和人工批准门。
- 当用户说“聚合广告报表”“把六张广告表合成一张”或“生成 ad_decision_packet”时，先读取 [聚合工具入口](tools/ad_report_aggregator/README.md)，调用 `scripts/build_ad_decision_packet.py`；不得让模型逐行手工重算六表。
- 聚合工具的 `DQ_PASS` 只表示数据包可进入人工分析，不表示广告动作通过或已经执行。

## 每次交付前

运行：

```bash
.venv/bin/python scripts/validate_project_scope.py
.venv/bin/python scripts/validate_v20_rules.py
.venv/bin/python scripts/validate_phase1_decisions.py
.venv/bin/python scripts/validate_integration_placeholders.py
.venv/bin/python scripts/validate_threshold_calibration.py
.venv/bin/python scripts/stress_test_threshold_calibration.py
.venv/bin/python scripts/stress_test_v21_provenance.py
.venv/bin/python -m pytest new_product_module/tests ai_ads/tests -q
.venv/bin/python -m pytest operator_console/backend/tests -q
cd operator_console && npm run lint && npm test && npm audit --omit=dev && cd ..
.venv/bin/python scripts/stress_test_ad_report_aggregator.py
.venv/bin/python scripts/stress_test_v20.py
.venv/bin/python scripts/v21_release_manifest.py
```

任一校验失败，不得宣称规则、阈值或智能体已完成。
