# 合同：历史数据阈值校准与人工批准

## 输入日粒度

每行必须包含：日期、`category=rug`、Calibration Segment ID、Rug 类型、尺寸档、广告类型、策略阶段、对象粒度、对象 ID、Marketplace、币种、曝光、点击、广告订单、花费、广告销售额、归因成熟状态、DQ 状态、验证窗口 ID 和来源引用。

不同 Segment、策略阶段、对象粒度、Marketplace 或币种不得直接合并。相同 Segment、日期、对象和策略阶段出现重复行时固定阻断。

## 候选包

候选包至少保存：

- Candidate ID、配置版本、生成时间；
- 输入文件 SHA-256；
- Threshold ID 和资格状态；
- 有效点击、广告订单、独立日期、验证窗口；
- CTR、CVR、CPC、CPA、ACOS；
- CVR 95% Wilson 区间；
- 日粒度 P25/P50/P75；
- 候选四档边界及适用粒度；
- 当前正式阈值文件 SHA-256（运行时必须与派生配置一致，否则阻断）；
- 训练期/留出期、独立对象数、可比较对象对、当前/候选留出一致率；
- 一致率提升及对象级 Bootstrap 95% 区间；
- `HISTORICALLY_BETTER_CANDIDATE / NOT_BETTER / INCONCLUSIVE` 证明状态；
- 数据问题、未达门槛差额和人工审批状态。

资格状态只允许：

- `INSUFFICIENT_DATA`；
- `ZERO_ORDER_RISK_CANDIDATE`；
- `REFERENCE_CANDIDATE`；
- `HIGH_CONFIDENCE_CANDIDATE`；
- `DQ_BLOCKED`。

## 人工批准

人工决定只允许 `APPROVED / REVISED / REJECTED / INSUFFICIENT_DATA`。批准必须包含 Candidate ID、候选文件 SHA-256、确认人、带时区确认时间、批准范围和备注。

`APPROVED` 只允许作用于 `HISTORICALLY_BETTER_CANDIDATE` 分组；证据为 `NOT_BETTER / INCONCLUSIVE` 时必须拒绝批准并继续补样本或修正候选。批准导入只能生成 `HUMAN_APPROVED_PENDING_REGRESSION` Change Set，不得直接修改当前正式阈值。正式更新仍需：

1. 人工把批准值维护到 `thresholds/`；
2. 分配或确认 Threshold ID；
3. 保存来源 SHA-256、适用粒度、生效日期和确认记录；
4. 完成边界、回放、Validator 和压力测试；
5. 重建 V2.0 manifest。

任何程序不得把候选或批准记录直接标记为机器 `ACTIVE`。
