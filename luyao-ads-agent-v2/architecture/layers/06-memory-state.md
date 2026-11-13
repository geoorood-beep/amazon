# 第 06 层：Memory-Augmented 状态与证据记忆

## 正式记忆

只有以下文件可以作为正式证据：

- Data Snapshot；
- AdContext；
- Rule Package manifest 和文件校验值；
- 最终方案；
- 实际执行确认；
- before / after 快照；
- 复盘证据和版本变化记录。

## 不属于正式记忆

- 聊天对话中的模型印象；
- 未冻结的屏幕观察；
- 没有来源和日期的口头结论；
- 历史 Markdown 中已经被替换的规则。

## 版本隔离

- 当前规则：`rules/`；
- 当前阈值：`thresholds/`；
- 历史快照：`history/`；
- V2 架构来源：`docs/v2/source/`；
- 规则证据和批次记忆：未来进入 `ai_ads/batches/` 和 `ai_ads/review/`，当前不伪造空的生产记录。
