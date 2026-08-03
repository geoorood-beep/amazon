# 陆遥广告智能体 V2.0 冻结发布

- 当前版本：`V2.0`
- 冻结状态：`V2.0_FROZEN`
- 冻结日期：`2026-08-04`
- 类目范围：仅 `rug`
- 执行边界：`HUMAN_EXECUTION_ONLY + TEST_ONLY`
- GitHub：`https://github.com/geoorood-beep/luyao-ads-agent-v2`（private）

## 冻结内容

本发布固定八层架构、人工规则、Rug阈值、合同、固定数据、P0/P1/P2修复、确定性校验器、回归测试、压力测试、第 05 层本地六表聚合工具和外部接入预留。每个纳入发布的文件及SHA-256记录在 `MANIFEST.sha256`。

本次冻结增量加入真实 7/14/30 天重叠报表名称键分析模式：30 天每日明细是唯一历史事实源，7/14 天与汇总表只校验；错误 XLSX 维度元数据可恢复读取；店铺口径与广告归因口径分离；缺 Amazon 不可变 ID 时允许分析但固定阻断执行。

本次冻结增量还加入 Rug 历史阈值校准：参考候选门为 2,000 有效点击、50 广告订单、14 个独立日；较高置信候选门为 5,000 点击、100 订单、30 日和 3 个验证窗口；300 点击、0 订单、14 日只生成风险候选。本地监控可累积 CSV、阻断重叠、生成时间留出证据并对同一 Candidate ID 只提醒一次。所有候选仍需人工批准和回归，程序不能覆盖正式阈值。

候选阈值包现在自动保存当前阈值 SHA-256，并在 `SKU_SIZE` 粒度上执行对象级时间留出对比：至少 20 个对象、100 对对象对、1,000 次 Bootstrap、留出一致率至少提高 5 个百分点；CVR/CPA/ACOS 至少两项显著更好且无一显著变差，才标记 `HISTORICALLY_BETTER_CANDIDATE`。反向留出表现会标记 `NOT_BETTER`，证据不足标记 `INCONCLUSIVE`，两者均不得人工批准为正式更新。

候选阈值监控默认周期固定为每周一 09:00、安装设备本地时区，不再使用每日检查。周期、唯一调度器策略和相对输入路径保存在可移植配置中；云存储与云端 Scheduler 已预留只读接入位，当前仍为 `PLACEHOLDER_NOT_ACTIVE`。

本次冻结增量加入本地运营网页第一版：新品推广、老品优化、更新广告数据、查看本周建议四个入口；网页只负责收集任务与展示结果，本地 Python 负责聚合，Codex Worker 使用只读沙箱按 V2.0 规则分析，独立 Validator 固定阻断执行权限。后台仅监听本机回环地址，任务文件不进入 Git，未接通 Amazon 或任何外部服务器。

无需业务定值即可确定的结构缺口已经进入合同与 Validator：预算类型/计算依据、流量角色/重叠意图、拓量执行对象、设置变更切段、赢家迁移、低置信度执行阻断、混合广告位/商品结构隔离。小时理想花费曲线因缺逐小时样本已撤下，不再输出过快/过慢标签。

冻结不代表启用Amazon后台自动执行。圆形Rug性能阈值、低样本强收缩Threshold ID和生产机器ACTIVE规则包仍保持阻断。MCP、HTTP API、Webhook 和其他外部服务器连接器当前均为 `PLACEHOLDER_NOT_ACTIVE`，没有真实 Endpoint 或运行服务。

## 验收结果

```text
项目边界校验                         PASS
V2.0规则一致性校验                   PASS
第一阶段裁决登记校验                  PASS
第05层外部接入占位校验                PASS
Python接口Schema重新导出              PASS（12份）
单元/回归测试                         PASS（114项，含阈值校准15项）
运营网页前端构建/渲染/Lint             PASS（2项页面测试）
运营网页独立Validator对抗测试           PASS（4项）
运营网页真实周检端到端                   PASS（NO_INPUT → DATA_REQUIRED → PASS_CANDIDATE_ONLY）
运营网页生产依赖审计                     PASS（0项漏洞）
候选阈值自动生成                      PASS（资格门、候选值、来源SHA-256）
历史留出更优证明                      PASS（正向证明、反向拒绝、证据不足阻断）
阈值校准压力测试                      PASS（6,000行、200分组、20次重放）
广告报表聚合确定性重放                PASS（50次）
广告报表聚合对抗输入                  PASS（9类正确阻断）
广告报表聚合容量                      PASS（15,000行 / 500词，0.403秒）
真实重叠报表去重                       PASS（27份来源、16项窗口检查）
聚合工作簿公式/16表渲染/ZIP完整性       PASS
随机反向动作                         PASS（2,000项）
动作仲裁                             PASS（50,000项，0.132秒）
Data Quality确定性重放               PASS（5,000次，0.0382秒）
真实Rug ABA与历史数据适配             PASS（468词，0.665秒）
重复历史词聚合与小数整数拒绝           PASS
```

时间数据为本机本次压力测试结果，用于回归基线，不作为其他设备的固定性能承诺。

## 校验命令

```bash
.venv/bin/python scripts/validate_project_scope.py
.venv/bin/python scripts/validate_v20_rules.py
.venv/bin/python scripts/validate_phase1_decisions.py
.venv/bin/python scripts/validate_integration_placeholders.py
.venv/bin/python scripts/validate_threshold_calibration.py
.venv/bin/python scripts/stress_test_threshold_calibration.py
.venv/bin/python -m pytest new_product_module/tests ai_ads/tests -q
.venv/bin/python -m unittest discover operator_console/backend/tests -v
cd operator_console && npm run lint && npm test && npm audit --omit=dev && cd ..
.venv/bin/python scripts/stress_test_ad_report_aggregator.py
.venv/bin/python scripts/stress_test_v20.py
.venv/bin/python scripts/v20_release_manifest.py
```
