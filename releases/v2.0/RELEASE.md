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

本地运营网页已固定到 V1.2：新品导入模式在表格识别前不显示空白基础信息，识别后生成可人工修改的字段；老品取消单独工作簿入口，原始广告报表支持多选、文件夹选择和一次拖拽。老品流程拆为“本地 Python 聚合”和“生成广告建议方案”两步，聚合完成前不调用 Codex，第二步复用现有数据包。完整 7/14/30 天报表可在无老品工作簿时运行重叠安全聚合；ASIN与日期从报表识别，缺不可变ID时仍固定阻断执行。上传文件只保存在本机 `runtime/operator-uploads/`，不进入 Git 或云端。

运营网页 V1.2 的视觉系统已统一为绿色与白色：左侧广告业务导航、浅灰工作区、白色圆角任务卡、绿色主操作和移动端自适应。新品、老品、拖拽上传、Python处理窗口、建议结果与 Validator 只调整呈现层，不改变业务路由、阈值、执行边界或两阶段任务状态。

运营网页新增可分享的公开演示模式，但访问主次固定为“本地主版本、公开分享附件”：启动命令始终打开 `http://localhost:3001/`，本地版保留上传、聚合、Codex分析和结果下载；公开链接只放在本地页脚的次要“分享演示版”入口。非 localhost 访问自动显示 `PUBLIC DEMO` 并关闭真实处理能力，广告数据不会发送到公开站点。

运营网页升级为 V1.3 独立网站结构：广告系统固定在本项目 `localhost:3001`，智能补货固定在独立项目 `localhost:3000`，两个站点通过顶部切换器双向跳转。广告站不再提供内部补货路由；两边不共享规则、阈值、上传文件、任务状态或执行权限。

无需业务定值即可确定的结构缺口已经进入合同与 Validator：预算类型/计算依据、流量角色/重叠意图、拓量执行对象、设置变更切段、赢家迁移、低置信度执行阻断、混合广告位/商品结构隔离。小时理想花费曲线因缺逐小时样本已撤下，不再输出过快/过慢标签。

冻结不代表启用Amazon后台自动执行。圆形Rug性能阈值、低样本强收缩Threshold ID和生产机器ACTIVE规则包仍保持阻断。MCP、HTTP API、Webhook 和其他外部服务器连接器当前均为 `PLACEHOLDER_NOT_ACTIVE`，没有真实 Endpoint 或运行服务。

## 验收结果

```text
项目边界校验                         PASS
V2.0规则一致性校验                   PASS
第一阶段裁决登记校验                  PASS
第05层外部接入占位校验                PASS
Python接口Schema重新导出              PASS（12份）
单元/回归测试                         PASS（126项，含运营网页后台12项）
运营网页前端构建/渲染/Lint             PASS（2项页面测试，含跨站导航边界）
运营网页独立Validator对抗测试           PASS（4项）
运营网页上传/字段/两阶段测试              PASS（8项，含属性库一致性、路径穿越阻断、多ASIN、重叠报表检测和只聚合不生成建议）
真实报表自动识别                       PASS（27份来源；无需老品工作簿；周期2026-05-31至2026-06-29）
真实报表重叠安全聚合                    PASS（B0H3642LQD；REPORT_ONLY_OVERLAP_SAFE_MULTI_ASIN；READY_WITH_WARNINGS；执行因缺不可变ID保持阻断）
运营网页真实两阶段端到端                 PASS（第一阶段0条建议并停在AGGREGATED；第二阶段复用聚合包生成5条建议；Validator保持禁止执行）
运营网页真实周检端到端                   PASS（NO_INPUT → DATA_REQUIRED → PASS_CANDIDATE_ONLY）
运营网页生产依赖审计                     PASS（0项漏洞）
候选阈值自动生成                      PASS（资格门、候选值、来源SHA-256）
历史留出更优证明                      PASS（正向证明、反向拒绝、证据不足阻断）
阈值校准压力测试                      PASS（6,000行、200分组、20次重放）
广告报表聚合确定性重放                PASS（50次）
广告报表聚合对抗输入                  PASS（9类正确阻断）
广告报表聚合容量                      PASS（15,000行 / 500词，0.384秒）
真实重叠报表去重                       PASS（27份来源、16项窗口检查）
聚合工作簿公式/16表渲染/ZIP完整性       PASS
随机反向动作                         PASS（2,000项）
动作仲裁                             PASS（50,000项，0.1262秒）
Data Quality确定性重放               PASS（5,000次，0.0387秒）
真实Rug ABA与历史数据适配             PASS（468词，0.6313秒）
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
