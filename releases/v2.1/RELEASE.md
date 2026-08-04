# 陆遥广告智能体 V2.1 运行时发布

- 运行时版本：`V2.1`
- 业务规则集：`V2.0_FROZEN`
- 网页版本：`V1.8`
- 类目：`rug`
- 执行边界：`HUMAN_EXECUTION_ONLY`
- Amazon 自动执行：关闭

## 本次固定内容

V2.1 修复“网页看起来调用 AGENTS，但无法证明最终结论确实来自同一套规则、阈值、数据和工具”的问题。当前固定处理链为：

```text
网页业务输入
→ Python 确定性预处理与证据包
→ 服务端可信意图路由
→ 八层 AGENTS 上下文与全部来源 SHA-256
→ Codex 结构化业务结论
→ 独立 Validator 重建上下文并核对工具/Codex/文件回执
→ 页面预览和最终工作簿
```

具体变化：

1. 请求不能覆盖 `config/operator_intents.json` 的服务端可信路由；路由不完全一致即阻断。
2. `agents_context.json` 覆盖 8/8 架构层，并登记规则、阈值、知识、配置、工具、合同和证据的 SHA-256。
3. Python 工具输入、配置、程序和输出生成确定性回执；Codex 保存运行编号、上下文摘要、输出路径和输出 SHA。
4. Validator 不信任结果自报，会独立重建上下文并核对完整 `sources_read`、证据来源、工具回执、Codex 原始 JSON 和最终文件。
5. 新品 Python 工作簿改为《新品候选证据包.xlsx》，不会直接作为页面或最终架构下载；最终《广告架构设计方案.xlsx》只从 Validator 通过的 `new_product_architecture` 生成。
6. SP广告优化同样只展示和导出 Validator 通过后的 Codex 结论；报表聚合仍是纯 Python 确定性任务，不调用 Codex、不生成广告动作。
7. 页面继续只展示用户输入、问题提示、结果预览和下载，不暴露内部规则路径与过程 JSON。

## 压力测试标准

- 四个网页意图的八层覆盖必须全部为 `8/8`；
- 10,000 个伪造上下文不得有任何一个通过；
- 篡改工具回执、缺少 Codex 来源、引用未登记证据、篡改 Codex 原始输出、篡改最终工作簿均必须阻断；
- V2.0 规则校验、新品与 ai_ads 测试、运营后台测试、前端测试、依赖审计、聚合压力测试、阈值校准压力测试和全项目压力测试必须全部通过。

## 发布校验

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

`releases/v2.1/MANIFEST.sha256` 是本运行时快照的冻结文件清单。V2.0 规则源和阈值单一真源仍分别位于 `rules/` 与 `thresholds/`，本次没有把网页逻辑变成新的业务规则源。
