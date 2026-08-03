# 陆遥广告智能体 V2.0 冻结发布

- 当前版本：`V2.0`
- 冻结状态：`V2.0_FROZEN`
- 冻结日期：`2026-08-03`
- 类目范围：仅 `rug`
- 执行边界：`HUMAN_EXECUTION_ONLY + TEST_ONLY`
- GitHub：`https://github.com/geoorood-beep/luyao-ads-agent-v2`（private）

## 冻结内容

本发布固定八层架构、人工规则、Rug阈值、合同、固定数据、P0/P1/P2修复、确定性校验器、回归测试、压力测试、第 05 层本地六表聚合工具和外部接入预留。每个纳入发布的文件及SHA-256记录在 `MANIFEST.sha256`。

本次冻结增量加入真实 7/14/30 天重叠报表名称键分析模式：30 天每日明细是唯一历史事实源，7/14 天与汇总表只校验；错误 XLSX 维度元数据可恢复读取；店铺口径与广告归因口径分离；缺 Amazon 不可变 ID 时允许分析但固定阻断执行。

无需业务定值即可确定的结构缺口已经进入合同与 Validator：预算类型/计算依据、流量角色/重叠意图、拓量执行对象、设置变更切段、赢家迁移、低置信度执行阻断、混合广告位/商品结构隔离。小时理想花费曲线因缺逐小时样本已撤下，不再输出过快/过慢标签。

冻结不代表启用Amazon后台自动执行。圆形Rug性能阈值、低样本强收缩Threshold ID和生产机器ACTIVE规则包仍保持阻断。MCP、HTTP API、Webhook 和其他外部服务器连接器当前均为 `PLACEHOLDER_NOT_ACTIVE`，没有真实 Endpoint 或运行服务。

## 验收结果

```text
项目边界校验                         PASS
V2.0规则一致性校验                   PASS
第一阶段裁决登记校验                  PASS
第05层外部接入占位校验                PASS
Python接口Schema重新导出              PASS（12份）
单元/回归测试                         PASS（99项，含聚合工具10项）
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
.venv/bin/python -m pytest new_product_module/tests ai_ads/tests -q
.venv/bin/python scripts/stress_test_ad_report_aggregator.py
.venv/bin/python scripts/stress_test_v20.py
.venv/bin/python scripts/v20_release_manifest.py
```
