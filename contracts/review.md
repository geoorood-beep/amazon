# 合同：复盘与候选规则

## ReviewEligibility

只允许：

- `READY`；
- `NOT_READY`。

形成规则证据必须有完整执行记录、已结束的观察和归因窗口、一致口径、外部事件标记以及重叠动作识别。

## EvidenceType

- `SUPPORT`；
- `OPPOSE`；
- `INCONCLUSIVE`；
- `SCOPE_LIMITED`；
- `CONFLICT`；
- `UNSTABLE`。

## 证据字段

至少保存 Batch ID、Action ID、Action Pack ID、Rule ID、Threshold ID、实际执行值、复盘指标、Marketplace、Category、AdProductType、StrategyProfile、BusinessMode、规则包版本、观察周期和外部事件。

## CANDIDATE 边界

复盘只能复制当前规则包后生成完整 CANDIDATE，并记录 Change Set。它不能覆盖 ACTIVE，也不能把单次结果直接写成全局规则。当前项目没有生产 ACTIVE 机器包，因此不得伪造候选对比闭环已经完成。
