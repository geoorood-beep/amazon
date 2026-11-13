# Rug 新品 Phrase / Broad 路由阈值

- 适用类目：`rug`
- 适用粒度：`SEARCH_TERM + CANONICAL_ROOT + MARKETPLACE_MONTH`
- 确认日期：`2026-08-04`
- 来源：用户确认本轮 Phrase / Broad 逻辑；尚未用相关性表和搜索量表回放校准
- 状态：`USER_APPROVED_PROVISIONAL / TEST_ONLY / HUMAN_EXECUTION_ONLY`
- 机器权限：只能生成人工候选，不得执行或自动覆盖正式阈值

## 词根月搜索量分层

| Threshold ID | 词根月搜索量 | 用途 |
|---|---:|---|
| `RUG-NP-DEMAND-001` | `<3,000` | 不单独新建投放；只保留候选 |
| `RUG-NP-DEMAND-002` | `3,000-9,999` | 条件测试；优先合并同意图词组，需人工确认 |
| `RUG-NP-DEMAND-003` | `10,000-29,999` | 可投测试层；匹配方式仍由语义和集中度决定 |
| `RUG-NP-DEMAND-004` | `30,000-99,999` | 中高量主力层；预算与分组优先级提高 |
| `RUG-NP-DEMAND-005` | `>=100,000` | 高量核心层；必须独立监控，不因高流量自动放宽相关性 |

区间左闭右开，最后一档无上界。

## 词根集中度

```text
Top3 占比 = 同词根月搜索量最高的3个去重完整查询搜索量合计 / 词根月搜索量
```

| Threshold ID | 条件 | 匹配候选 |
|---|---:|---|
| `RUG-NP-CONCENTRATION-001` | 有效完整查询数 `<=3` | Phrase |
| `RUG-NP-CONCENTRATION-002` | Top3 占比 `>=60%` | Phrase |
| `RUG-NP-CONCENTRATION-003` | Top3 占比 `>=35%` 且 `<60%` | Phrase 承接 + Broad 探索，分组 |
| `RUG-NP-CONCENTRATION-004` | Top3 占比 `<35%` | Broad 低预算探索 |

明确尺寸、场景、材质、风格、颜色或形状是 Phrase 语义优先条件，但必须先通过相关性门和 `RUG-NP-DEMAND-001`。

## 时间窗口与去重

| Threshold ID | 数值 | 含义 |
|---|---:|---|
| `RUG-NP-VOLUME-WINDOW-001` | 最低 `1` 个完整自然月 | 可生成人工候选，标记短窗口 |
| `RUG-NP-VOLUME-WINDOW-002` | 优选最近 `3` 个完整自然月 | 对每月词根合计与 Top3 占比取中位数 |

去重键是 `Marketplace + 月份 + 标准化完整搜索词`。同一月份中的 7 / 14 / 30 天重叠表不得累加；同一完整搜索词不得同时归入多个规范词根。

## 待回放校准

用户补充相关性表和搜索量表后，需检查：

- `<3,000` 不独立投放是否错过高转化长尾；
- `35% / 60%` 集中度分界在 Rug 不同尺寸和场景中是否稳定；
- 一个月与三个月中位数的匹配方式稳定率；
- Phrase / Broad 分组后的查询重叠、CPC、CVR、CPA 和 ACOS。

回放未完成前，本文件不得标记为生产机器 `ACTIVE`。
