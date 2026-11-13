# 候选阈值云存储与云端定时任务接入位

当前状态：`PLACEHOLDER_NOT_ACTIVE`。

本接入位用于未来把 Rug 日粒度校准 CSV 放到对象存储，并在云端每周运行同一套候选阈值程序。当前没有云存储 Provider、Bucket、Endpoint、凭据或云端定时任务，不得宣称已经接通。

## 固定运行方式

- 默认周期仍为[监控配置](../../config/threshold_monitoring.json)中的每周一次；迁移到云端不得擅自变成每日任务。
- 本地与云端调度器只能有一个处于 ACTIVE，防止重复生成和重复提醒。
- 云端运行必须调用 `scripts/monitor_threshold_candidates.py`，不得另写一套候选规则或阈值。
- 云端输入只读；候选输出仍为 `CANDIDATE_ONLY`，不能改写 `thresholds/` 或调用 Amazon 后台。

## 云端对象清单

每个同步批次必须提供：

- `category=rug`；
- Provider、Bucket/Container、对象 Key；
- Object Version 或 ETag；
- 文件 SHA-256、字节数和更新时间；
- Marketplace、币种、日期范围和归因成熟状态；
- 同步批次 ID 和原始来源引用。

云端文件先进入本地或云端隔离区，完成 SHA-256、字段、重复日粒度、跨类目和归因校验后，才可送入阈值校准器。

## 激活条件

从 `PLACEHOLDER_NOT_ACTIVE` 升级前必须具备：

1. 用户确定的云存储 Provider 和账户范围；
2. 凭据只通过 Secret Manager 或环境变量引用；
3. 只读 Bucket/Container 权限和路径白名单；
4. 分页、超时、重试、版本锁和幂等同步；
5. 空对象、伪造 SHA、重复版本、跨类目、过期数据和部分下载测试；
6. 云端互斥锁，确保本地和云端不会同时提醒；
7. 与本地当前版本相同的完整回归、阈值压力测试和 V2.0 Manifest 校验；
8. 人工把 `cloud_storage` 和 `cloud_runner` 状态升级为 `TEST_ONLY`。

云端接通后仍不获得正式阈值写入权或广告执行权。
