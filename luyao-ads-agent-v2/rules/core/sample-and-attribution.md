# 核心规则：样本、归因与否词权限

## 低样本

- 订单样本未达到最低门时，默认 `DATA_INSUFFICIENT`，只允许观察。
- 唯一强收缩例外要求：无订单、归因成熟、命中已确认停止线、对象唯一映射且数据质量通过。
- 即使满足例外，也只能生成 `APPROVAL_REQUIRED` 候选，不能自动执行。
- 单个历史经验信号不能独立触发 Negative Exact、暂停或降 Bid。

最低样本、归因等待期和停止线只从以下阈值文件读取：

- `thresholds/rug/governance.md`；
- `thresholds/rug/performance.md`；
- `thresholds/rug/pending.md`。

当前低样本点击/花费停止线缺可执行 Threshold ID，因此机器强收缩固定阻断。低样本的数值定义只见 `thresholds/rug/performance.md`。

## Negative Exact

可执行 Negative Exact 必须同时满足完整报表模式、成熟归因、确认停止线、唯一 Target 映射、完整执行字段和 Validator 通过。否则只能写成待映射、待归因成熟或未到停止线候选。

新品流量隔离 Negative Exact 另按 `rules/domains/new-product/negative-isolation.md` 处理，不能与老品低效否词混为同一规则。
