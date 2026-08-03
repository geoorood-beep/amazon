# 核心规则：唯一整体状态

同一分析对象必须按以下优先级只输出一个状态：

```text
DATA_BLOCKED
DATA_INSUFFICIENT
TARGET_CATEGORY_RISK_CONFLICT
HIGH_RISK_WITH_VOLUME
HIGH_RISK_WITHOUT_VOLUME
EFFICIENT_AT_TARGET
EFFICIENT_STRUCTURE_RISK
EFFICIENT_UNDERSCALE
VOLUME_ACHIEVED_COST_ABOVE_TARGET
COST_ABOVE_TARGET_UNDERSCALE
INCONCLUSIVE
```

## 规则

1. 数据和样本状态优先于业务好坏。
2. 用户目标是经营目标；Rug 高风险线是风险护栏。
3. 用户目标宽于护栏且实际结果位于两者之间时，固定为 `TARGET_CATEGORY_RISK_CONFLICT`。
4. 风险冲突状态不得自动扩量或收缩，只能人工审批。
5. 整体状态先于预算、Bid、广告位、搜索词和结构诊断。

状态所用区间只从 `thresholds/rug/performance.md` 读取。
