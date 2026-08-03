# 合同：小白运营入口任务

状态：`V2.0 / HUMAN_EXECUTION_ONLY`。

网页只提交业务意图和输入，不保存业务规则或阈值。允许意图固定为：

- `NEW_PRODUCT_PROMOTION`；
- `OLD_PRODUCT_OPTIMIZATION`；
- `AGGREGATE_REPORTS`；
- `WEEKLY_REVIEW`。

每个任务必须保存 `job_id`、意图、`category=rug`、创建时间、输入字段、输入文件引用、AGENTS/规则/阈值版本、预处理状态、Codex结果和 Validator结果。

## V1.2 输入合同

### 新品推广

- 必填：`asin`、`marketplace`、`size_spec`、`rug_type`、`order_target_daily`；
- 可选：`sku`、`style`、`color`、`material`、`scene_tags`、`target_cpa`、`daily_budget`；
- `size_spec / rug_type / style / color / material / scene_tags` 的允许值只从 [本地属性库](../config/operator_catalog.json) 读取；
- 允许人工选择或上传一张 XLSX/XLSM/CSV/TSV。选择导入模式后，识别完成前不得显示空的产品基础信息表单；识别完成后生成可人工修改的表单。导入器只自动填入能映射到本地属性库的值，未知值必须提示人工选择；
- 不再收集“这次希望解决什么”。

### 老品优化和报表更新

- 必填：`marketplace`、后台生成的 `report_source_path`；
- `asin` 可为空、单个或多个。多个 ASIN 用逗号或空格分隔；为空时取广告商品报表 ASIN；识别超过 100 个 ASIN 时阻断并要求人工指定范围；
- `period_start / period_end` 不接受网页人工输入，必须由 Python 从上传表格日期列得到；
- “广告报表文件”是唯一的老品网页数据入口，可多选、拖拽或选择整个文件夹；网页不得再展示或接收“老品数据工作簿”；
- 网页上传文件保存到 `runtime/operator-uploads/<upload_id>/`，路径由后台生成。文件名必须保留，以便识别 7/14/30 天窗口；
- 多 ASIN 名称键模式按 ASIN 分目录生成数据包，任何单个 ASIN 失败必须独立记录，不得冒充成功。

固定状态：

```text
QUEUED
→ PREPROCESSING
→ ANALYZING
→ VALIDATING
→ COMPLETED / BLOCKED / FAILED
```

老品优化额外使用 `workflow_phase` 控制两步流程：`AGGREGATE_ONLY → AGGREGATED → ANALYSIS_REQUESTED → ANALYZED`。聚合完成前不得显示“生成广告建议方案”；点击第二步后复用 `preprocessing.json`，不得重复运行聚合。聚合失败使用 `AGGREGATION_BLOCKED`，分析或 Validator 失败使用 `ANALYSIS_BLOCKED`。

网页和 Codex Worker 均不得输出已执行状态。所有建议固定为 `CANDIDATE_ONLY`，最后只能“确认并导出执行表、重新分析、拒绝方案”。Amazon 后台连接和自动执行保持关闭。

任务运行目录位于 `runtime/operator-jobs/<job_id>/`，不纳入 V2.0 规则包或 Git。网页路由只读 [operator_intents.json](../config/operator_intents.json)，具体规则、阈值和输出字段仍从其单一真源读取。
