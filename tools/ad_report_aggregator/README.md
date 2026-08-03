# 广告报表聚合工具（V2.0）

状态：`ACTIVE_LOCAL_TOOL`。位置：第 05 层 Tool-Augmented。执行边界：`HUMAN_EXECUTION_ONLY`，不会登录或修改 Amazon 后台。

## 直接作用

本工具把同一 Rug 账户、同一链接、同一周期的六类 SP 报表在本地转为一个可直接供智能体读取的数据包：

1. `SP搜索词-按词-每日明细`；
2. `SP搜索词-按词-汇总`；
3. `SP投放对象 / 关键词 / 商品投放报告`；
4. `SP广告位报告`；
5. `SP广告商品报告`；
6. `Campaign / Ad Group 设置表`。

输出目录包含：

- `ad_decision_packet.json`：智能体优先读取的紧凑结构化数据；
- `ad_decision_packet.xlsx`：人工查看、筛选和追溯的工作簿；
- `data_quality_report.json`：数据质量状态和问题；
- `aggregation_manifest.json`：源文件、周期、SHA-256 和输出索引。

工作簿中的 `01_AGENT_INPUT` 是唯一聚合输入表。它把不同 `object_type` 和 `window` 保持为独立粒度，避免把搜索词、Target、广告位和商品报表重复相加。

## 对话自动路由

用户说“聚合广告报表”“把六张广告表合成一张”或“生成 ad_decision_packet”时，智能体应调用：

```bash
.venv/bin/python scripts/build_ad_decision_packet.py \
  --source-dir "/绝对路径/六张报表目录" \
  --context "/绝对路径/本批次context.json" \
  --output-dir "/Users/leo/Documents/陆遥广告智能体/outputs/本批次"
```

上下文模板：[ad_report_context.example.json](../../config/ad_report_context.example.json)。文件名无法唯一识别时，复制并填写[人工映射模板](../../config/ad_report_map.example.json)，再增加：

```bash
--report-map "/绝对路径/report_map.json"
```

## 固定处理顺序

```text
类目/上下文门
→ 六表文件识别
→ 工作表与字段别名映射
→ 数值、日期、币种和站点校验
→ Campaign / Ad Group / Target / 搜索词父级链
→ D3 / D7 / D14 / D30 本地聚合
→ 每日明细 × 汇总同粒度对账
→ AdDecisionPacket + 人工工作簿
→ Data Quality
```

技术金额容差固定为 `0.01 币种单位`，只处理二位小数舍入，不是 ACOS、CPA、CVR、Bid 或预算阈值。广告业务阈值仍只从 `thresholds/` 读取。

## 必须阻断

- `category` 不是 `rug`；
- 六类必需报表缺失、空表或同类多文件未人工映射；
- 周期、站点、币种或归因窗口冲突；
- 必填列缺失、列名映射不唯一或关键数值无法解析；
- 点击大于曝光、订单大于点击、订单不是整数或指标为负数；
- Campaign、Ad Group、Target、搜索词父级链冲突；
- 每日搜索词与汇总搜索词在同粒度对账失败；
- 完整模式不足 30 个自然日。

`DQ_PASS` 只表示数据包可以进入人工广告分析，不代表已经执行任何广告动作。

## 本地验证

```bash
.venv/bin/python -m pytest ai_ads/tests/test_report_aggregation.py -q
.venv/bin/python scripts/stress_test_ad_report_aggregator.py
```

当前发布验收使用合成六表完成。真实 Amazon 六表样本的字段变体仍需在第一次实际运行时做一次人工验收；若表头不同，应只更新 [ad_report_aggregation.json](../../config/ad_report_aggregation.json) 的别名，不在程序中临时猜列。
