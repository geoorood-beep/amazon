# Rug 预算与新品隔离阈值

## 标准最低日预算

状态：`CONFIRMED_HUMAN`。各 Rug 类型的 CPA 正常线上限只维护在 `performance.md`，本文不复制该数值。

公式：

```text
标准最低日预算 = CPA 正常线上限 × 单广告组目标订单数
```

没有显式单广告组目标时按 `1` 单计算。低于计算值只能标记观察预算或拓词预算。人工查值时先打开 `performance.md`，不得在本文另建一张数值表。

## 新品高流量核心隔离

- 状态：`HUMAN_RULE_FIXED / MACHINE_CANDIDATE_ONLY`
- 适用：Auto Close、关键词 Broad、Phrase。
- 推荐层级：`P1 / P2`。
- ABA 排名：`<=11,000`。
- 合规：`安全`。
- 其他要求：产品属性不冲突、当前广告组可能触达、不是本组投放对象。
- 否定方式：只允许 `Negative Exact`。

该门是流量隔离，不是低效否词。不得对本组主投词进行自我否定。
