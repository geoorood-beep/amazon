# 合同：小白运营入口任务

状态：`V2.1_RUNTIME / V2.0_RULESET / HUMAN_EXECUTION_ONLY`。

网页只提交业务意图和输入，不保存业务规则或阈值。允许意图固定为：

- `NEW_PRODUCT_PROMOTION`；
- `OLD_PRODUCT_OPTIMIZATION`；
- `AGGREGATE_REPORTS`；
- `WEEKLY_REVIEW`。

每个任务必须保存 `job_id`、意图、`category=rug`、创建时间、输入字段、输入文件引用、AGENTS/规则/阈值版本、预处理状态、Codex结果和 Validator结果。后台必须额外生成 `agents_context.json`：从服务端可信的 `operator_intents.json` 解析本意图登记的八层架构、规则、阈值、知识、配置、工具、合同和本次证据，并保存每项 SHA-256。请求中自带的路由只能与可信路由完全一致，不能覆盖服务端路由。任一登记来源缺失或哈希变化即阻断。

## V1.8 页面与输入合同

业务任务的固定链为：Python 确定性预处理并生成工具回执 → Codex 按 `agents_context.json` 生成结构化结论并生成运行回执 → 独立 Validator 重新构建上下文、复核两类回执及证据来源 → 页面和工作簿渲染。广告架构、优化建议、预算、Bid、匹配方式等业务结论不得由网页或 Python 预处理结果直接充当最终结果。聚合报表意图是例外：它只输出确定性数据包，不调用 Codex，也不得输出广告建议。

### 双系统网站边界

- 广告系统是当前项目的独立网站，本机固定入口为 `http://localhost:3001/`，保留广告架构设计、SP广告优化、报表聚合和每周建议四个广告意图；
- 智能补货是 `/Users/leo/Documents/陆遥智能补货智能体` 的独立网站，本机入口为 `http://localhost:3000/`；广告项目不提供内部补货路由；
- 两个网站只通过 `system-switcher.tsx` 的明确链接互相跳转，不共享规则、阈值、任务状态、上传文件、登录态或执行权限；
- 广告 Codex Worker 不得读取补货项目的业务规则、策略和运行数据生成广告动作；补货页面也不得提交广告 `operator-job`。

### 广告架构设计（内部兼容意图 `NEW_PRODUCT_PROMOTION`）

- 必填：`asin`、`marketplace`、`size_spec`、`rug_type`、`order_target_daily`；
- 可选：`sku`、`style`、`color`、`material`、`scene_tags`、`target_cpa`、`daily_budget`；
- `size_spec / rug_type / style / color / material / scene_tags` 的允许值只从 [本地属性库](../config/operator_catalog.json) 读取；
- 手动模式先填写一条产品信息，再点击“添加到产品清单”。同一任务最多保存 10 个不重复 ASIN，允许逐条编辑和删除；达到 10 个后必须在页面明确提示改用表格上传，不得静默丢弃第 11 条；
- 允许上传一张 XLSX/XLSM/CSV/TSV 批量表。选择导入模式后，识别完成前不得显示空的产品基础信息表单；识别完成后逐行生成可人工修改的产品清单。单次表格最多 100 个不重复 ASIN，重复 ASIN 保留首次记录并提示；
- 网页提交 `products_json` 保存本次完整产品清单，同时保留第一条产品的顶层字段兼容旧任务；后端必须逐 ASIN 运行同一规则管线，输出合并的两表工作簿，不得只分析最后填写的一条；
- 导入器只自动填入能映射到本地属性库的值，未知值必须提示人工选择；
- 不再收集“这次希望解决什么”。
- 广告架构设计自动区分 `HISTORY_ASSISTED` 与 `ABA_COLD_START`。冷启动允许在没有当前 ASIN 历史点击时生成 ABA+属性门候选，但始终是 `CANDIDATE_ONLY`；历史样本阈值缺失不得阻断冷启动候选，也不得冒充历史验证。

### SP广告优化（内部兼容意图 `OLD_PRODUCT_OPTIMIZATION`）和报表更新

- 必填：`marketplace`、后台生成的 `report_source_path`；
- `asin` 可为空、单个或多个。多个 ASIN 用逗号或空格分隔；为空时取广告商品报表 ASIN；识别超过 100 个 ASIN 时阻断并要求人工指定范围；
- `period_start / period_end` 不接受网页人工输入，必须由 Python 从上传表格日期列得到；
- “广告报表文件”是唯一的老品网页数据入口，可多选、拖拽或选择整个文件夹；网页不得再展示或接收“老品数据工作簿”；
- 网页上传文件保存到 `runtime/operator-uploads/<upload_id>/`，路径由后台生成。文件名必须保留，以便识别 7/14/30 天窗口；
- 多 ASIN 名称键模式按 ASIN 分目录生成数据包，任何单个 ASIN 失败必须独立记录，不得冒充成功。
- 聚合脚本即使生成了数据包，只要存在 blocking 数据质量问题，任务状态必须是 `BLOCKED`；不得把 openpyxl 的非致命样式警告当成真实失败原因，也不得把 `DATA_REQUIRED` 显示成已完成。

固定状态：

```text
QUEUED
→ PREPROCESSING
→ ANALYZING
→ VALIDATING
→ COMPLETED / BLOCKED / FAILED
```

SP广告优化额外使用 `workflow_phase` 控制两步流程：`AGGREGATE_ONLY → AGGREGATED → ANALYSIS_REQUESTED → ANALYZED`。聚合完成前不得显示“生成 SP 广告优化方案”；点击第二步后复用 `preprocessing.json`，不得重复运行聚合。聚合失败使用 `AGGREGATION_BLOCKED`，分析或 Validator 失败使用 `ANALYSIS_BLOCKED`。

网页和 Codex Worker 均不得输出已执行状态。所有建议固定为 `CANDIDATE_ONLY`，最后只能“确认并导出执行表、重新分析、拒绝方案”。Amazon 后台连接和自动执行保持关闭。

网页默认只展示四类内容：用户需要填写或上传的输入、需要人工处理的问题提示、结果预览、结果文件下载。不得默认展示 AGENTS 路由、规则与阈值文件路径、Threshold ID、SHA、工具清单、内部提示词、Validator 枚举、过程 JSON 或中间产物。广告架构设计的结果区只展示“新广告设置表”的网页预览、广告架构工作簿下载按钮和问题提示；ABA 选词证据仍保留在下载工作簿中供复核。SP 广告优化、广告数据更新和每周建议遵守同一原则，只展示用户决策所需的结果字段。

任务运行目录位于 `runtime/operator-jobs/<job_id>/`，不纳入 V2.0 规则包或 Git。网页路由只读 [operator_intents.json](../config/operator_intents.json)，具体规则、阈值和输出字段仍从其单一真源读取。业务结果必须带 `CODEX_AGENTS` 来源、上下文摘要、完整 `sources_read`、工具回执编号和 Codex 回执；Validator 通过前不得生成或公开最终工作簿。
