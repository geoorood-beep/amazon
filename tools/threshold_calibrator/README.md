# Rug 历史阈值校准工具

状态：`ACTIVE_LOCAL_TOOL / CANDIDATE_ONLY / HUMAN_APPROVAL_REQUIRED`。

本工具检查历史广告样本是否达到 `THR-CAL-001/002/003`，自动生成候选阈值包，并按 `THR-CAL-004` 在未参与拟合的历史留出期中回放当前阈值和候选阈值。它保存样本差额、指标分布、当前阈值 SHA-256、对象对一致率、Bootstrap 区间和人工批准 Change Set。它不会修改正式阈值，也不会操作 Amazon 后台。

## 放入数据

把符合[样本示例](../../config/threshold_calibration_samples.example.csv)的一个或多个 CSV 放入：

```text
<项目根目录>/imports/threshold-calibration/
```

相同 Segment、日期、对象和策略阶段不得在多个文件中重复。

## 达标检查

```bash
.venv/bin/python scripts/check_threshold_calibration.py \
  --source-dir "imports/threshold-calibration" \
  --output-dir "outputs/threshold-calibration/latest"
```

输出：

- `threshold_candidate.json`；
- `threshold_candidate.md`；
- `threshold_calibration_status.json`；
- `notification.md`（只有正式候选分组达标时生成）。

候选包中的 `proof_status`：

- `HISTORICALLY_BETTER_CANDIDATE`：至少两项留出一致率显著提升且没有指标显著变差；
- `NOT_BETTER`：至少一项显著变差；
- `INCONCLUSIVE*`：对象、对象对、粒度或证据不足。

证明只适用于与当前性能阈值一致的 `SKU_SIZE` 粒度。Target、搜索词、Campaign 等数据仍可累计资格样本，但不得据此声称新的 SKU_SIZE 性能阈值更好。

## 固定监控周期

便携配置：[threshold_monitoring.json](../../config/threshold_monitoring.json)。默认每周一 `09:00`，使用安装设备本地时区；不创建每日任务。同一项目只允许一个活动 Heartbeat。

当前本地目录是唯一活动数据源。未来云存储和云端 Scheduler 的字段、互斥要求和激活门见[云端接入位](../../integrations/cloud/threshold-monitoring-cloud-slot.md)，当前状态为 `PLACEHOLDER_NOT_ACTIVE`。

## 人工批准

复制[批准示例](../../config/threshold_candidate_approval.example.json)，填写 Candidate ID、候选文件 SHA-256、决定、确认人、时间和范围，然后运行：

```bash
.venv/bin/python scripts/approve_threshold_candidate.py \
  --candidate "/绝对路径/threshold_candidate.json" \
  --approval "/绝对路径/approval.json" \
  --output "/绝对路径/threshold_change_set.json"
```

`APPROVED` 只接受 `HISTORICALLY_BETTER_CANDIDATE` 分组，并生成 `HUMAN_APPROVED_PENDING_REGRESSION`，不自动覆盖 `thresholds/`。正式更新必须继续经过人工维护、回归、压力测试和 V2.0 manifest。
