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
- [广告报表聚合工具](../../tools/ad_report_aggregator/README.md)：六类 SP 报表本地聚合，状态为 `ACTIVE_LOCAL_TOOL`；
- [本地运营网页](../../operator_console/README.md)：独立广告网站，保留新品、老品、报表更新和本周建议四入口；顶部链接可跳转到独立补货网站，状态为 `ACTIVE_LOCAL_UI_V1_3`；
- [运营属性库](../../config/operator_catalog.json)：新品尺寸、类型、风格、颜色、材质和场景选项，状态为 `ACTIVE_LOCAL_CATALOG`；
- `operator_console/backend/table_recognizer.py`：上传表格字段、ASIN和日期识别，状态为 `ACTIVE_LOCAL_TOOL`；
- [历史阈值校准合同](../../contracts/threshold-calibration.md)：本地累计日粒度历史数据、生成候选阈值和一次性提醒，状态为 `CANDIDATE_ONLY`；
- `scripts/`：数据导入、聚合入口与项目校验；
- `contracts/README.md`：工具必须遵守的字段合同。

## 本地六表聚合（已启用）

当用户要求“聚合广告报表”时，调用：

```bash
.venv/bin/python scripts/build_ad_decision_packet.py \
  --source-dir "/绝对路径/六表目录" \
  --context "/绝对路径/context.json" \
  --output-dir "/Users/leo/Documents/陆遥广告智能体/outputs/本批次"
```

程序在本机读取 CSV/TSV/XLSX，生成 `ad_decision_packet.json`、`ad_decision_packet.xlsx`、数据质量报告和证据清单。字段与粒度见[广告报表聚合合同](../../contracts/ad-report-aggregation.md)。它不调用 LLM 逐行计算，也不连接或修改 Amazon 后台。

若用户提供的是 7/14/30 天重叠导出且缺 Amazon 不可变 ID，则调用名称键分析入口。网页不要求老品工作簿；命令行的 `--old-product-workbook` 仅保留为旧批次兼容选项：

```bash
.venv/bin/python scripts/build_name_keyed_ad_analysis.py \
  --source-dir "/绝对路径/产品广告数据文件" \
  --old-product-workbook "/绝对路径/老品优化.xlsx" \
  --primary-asin "B0XXXXXXXXX" \
  --output-dir "/Users/leo/Documents/陆遥广告智能体/outputs/本批次" \
  --render-previews
```

该入口固定以 30 天每日明细为历史事实源，7/14 天和汇总文件只做一致性校验；店铺口径与广告归因口径分离。名称哈希不能替代 Amazon ID，因此输出只允许分析，执行状态固定阻断。

本地聚合工具与外部接入网关是两件事：本地聚合已经启用；MCP、API、Webhook 和外部服务器仍未启用。

## 本地运营网页（V1.3 已启用）

双击项目根目录的 `运行广告运营台.command`，打开 `http://localhost:3001/`。新品属性可从本地属性库选择，也可上传产品表自动识别；导入模式只在识别完成后生成可编辑基础信息。老品和报表更新可多选、拖拽或选择文件夹上传原始广告报表，Python 自动识别 ASIN 和数据周期。用户不再手填本机路径或日期。任务和上传文件分别保存在被 Git 忽略的 `runtime/operator-jobs/` 与 `runtime/operator-uploads/`。

老品网页取消单独工作簿入口。用户先点击“聚合数据报表”，只运行本地 Python；成套 7/14/30 天报表使用报表内 ASIN 生成重叠安全分析包。聚合成功后才出现“生成广告建议方案”，第二步复用数据包并调用只读 Codex，最后由独立 Validator 校验。ASIN 输入为空表示自动识别，填写一个或多个表示只分析指定对象。

四个入口及其规则/阈值路由登记在 `config/operator_intents.json`，字段与状态读取[运营任务合同](../../contracts/operator-job.md)。网页不得复制或维护业务阈值，不得把 `PASS_CANDIDATE_ONLY` 解释为已经执行。后台只监听本机 `127.0.0.1:8766`，不属于外部 API 接入激活。

网站结构已经拆分：广告系统仅在本项目的 `localhost:3001` 运行；智能补货在独立项目的 `localhost:3000` 运行。顶部系统切换器只做站点跳转，不共享规则、阈值、上传文件、任务状态或执行权限。

## 本地候选阈值监控（已启用）

监控读取 `imports/threshold-calibration/*.csv`，按日粒度去重并累计点击、广告订单、独立天数和验证窗口：

```bash
.venv/bin/python scripts/monitor_threshold_candidates.py
```

具体样本门直接读取[历史校准资格阈值](../../thresholds/rug/calibration-eligibility.md)，字段读取[校准合同](../../contracts/threshold-calibration.md)。监控只生成 `CANDIDATE` 和历史留出证据；人工批准后仍为 `HUMAN_APPROVED_PENDING_REGRESSION`，不会修改正式阈值或 Amazon 后台。完整的数据落地、云端边界和提醒流程见[自动累积与提醒正文](../../docs/v2/候选阈值自动累积与提醒.md)。

默认调度固定为每周一 `09:00`、安装设备本地时区，机器配置见[阈值监控配置](../../config/threshold_monitoring.json)。复制到其他电脑后仍读取项目相对路径；调度器不可用时只报告未调度，不创建未经允许的系统任务。未来云存储和云端 Scheduler 使用[云端接入位](../../integrations/cloud/threshold-monitoring-cloud-slot.md)，当前保持占位禁用。

## 外部接入网关预留

第 05 层已为外部服务器、MCP 和 API 预留统一入口：[外部接入网关正文](../../integrations/external-integration-gateway.md)。当前状态固定为 `PLACEHOLDER_NOT_ACTIVE`，没有运行中的 Endpoint 或连接器。

| 接入类型 | 预留正文 | 当前权限 |
|---|---|---|
| MCP Client / MCP Server | [MCP 接入位正文](../../integrations/mcp/mcp-connection-slot.md) | 不可连接 |
| HTTP API / Webhook | [API 接入位正文](../../integrations/api/http-api-webhook-slot.md) | 不可监听、不可调用 |
| 其他外部服务器 | [服务器接入位正文](../../integrations/server/external-server-slot.md) | 不可连接 |
| 统一入库和隔离 | [入库接入位正文](../../integrations/ingestion/ingestion-pipeline-slot.md) | 不创建生产批次 |
| 云存储 / 云端每周任务 | [候选阈值云端接入位](../../integrations/cloud/threshold-monitoring-cloud-slot.md) | 不可连接、不可调度 |

所有未来连接器必须先生成 [ExternalDataEnvelope](../../contracts/external-ingest.md)，保存原始输入和 SHA-256，再转换为 `AdDecisionPacket / AdContext`。外部输入不得直接携带 `DQ_PASS`、`AUTO_PASS`、`ACTIVE` 或广告动作权限。

占位配置见 [connectors.example.yaml](../../config/connectors.example.yaml)。修改占位状态前必须运行 `scripts/validate_integration_placeholders.py` 并新增真实连接器测试。
