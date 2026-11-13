# Rug Category Historical Search Terms

## 类目

- 中文：地毯 / Rug
- 英文：rug / area rug / runner rug / doormat / kitchen rug / bathroom rug / round rug
- 用途：用于 Rug 新品推广、新广告搭建和搜索词复用时的同类历史出单词 / 效果词参考。

## 数据来源

| 来源产品 | 原始文件 | 原始时间范围 | 入库 raw 文件 |
|---|---|---|---|
| 冬豚 | `/Users/leo/Downloads/亚马逊-冬豚-US-US-关键词分析-0408-0706-汇总-932758699202043904.xlsx` | 2026-04-08 至 2026-07-06 | `raw/20260707_rug_冬豚_US_keyword_analysis_0408-0706.xlsx` |
| 岚风 | `/Users/leo/Downloads/亚马逊-岚风-US-US-关键词分析-0106-0706-汇总-932759690372714496.xlsx` | 2026-01-06 至 2026-07-06 | `raw/20260707_rug_岚风_US_keyword_analysis_0106-0706.xlsx` |

源表类型为关键词分析汇总表，不是 Amazon 原始 Search Term Report。源表有关键词、中文翻译、广告活动投放数量、曝光、点击、CTR、CPC、花费、广告销售额、直接/间接销售额、ACOS、ROAS、广告订单、直接/间接订单、CPA、CVR 等字段。

## 标准化文件

| 文件 | sheet | 行数 | 说明 |
|---|---|---:|---|
| `normalized/20260707_rug_historical_search_terms_normalized.xlsx` | `historical_order_terms` | 905 | 两个来源产品中 `广告订单 > 0` 的历史出单词明细 |
| `normalized/20260707_rug_historical_search_terms_normalized.xlsx` | `term_summary` | 818 | 按 `search_term` 聚合后的跨来源效果词表 |

## 汇总指标

| 来源产品 | 出单词行数 | 唯一词数 | 广告订单 | 点击 | 花费 | 广告销售额 |
|---|---:|---:|---:|---:|---:|---:|
| 冬豚 | 293 | 287 | 32,640 | 540,780 | 306,899.85 | 1,516,791.70 |
| 岚风 | 612 | 611 | 13,948 | 305,737 | 236,744.90 | 767,135.49 |
| 合计 | 905 | 818 | 46,588 | 846,517 | 543,644.75 | 2,283,927.19 |

## 子类目分布

| 子类目 | 出单词行数 |
|---|---:|
| area rug | 572 |
| runner rug | 148 |
| kitchen rug | 63 |
| rug | 44 |
| round rug | 37 |
| doormat | 22 |
| bathroom rug | 19 |

## 数据置信度

数据置信度：中。

原因：

1. 有明确时间范围、点击、花费、订单、销售额、CPA、CVR 和 ACOS。
2. 源表是关键词分析汇总表，缺 Campaign / Ad Group 明细。
3. 源表字段是关键词维度，不等同于当前链接真实搜索词报表。

## 使用规则

1. 本数据只能作为 Rug 类目新品选词、新广告候选词和搜索词复用参考。
2. 使用前必须先按当前产品的地毯区域、尺寸、颜色、风格、材质和图案动物类型做产品匹配。
3. 历史出单词优先级高于通用 ABA 候选，但仍必须通过 ABA 阶段区间、合规状态和产品属性匹配。
4. 当前产品是具体动物图案时，必须遵守 `agents/new-product-promotion.md` 的 `图案动物类型` 强匹配规则，不得因为某动物词在历史库出过单就推荐给其他动物图案产品。
5. 本数据不能作为老品推广诊断源，不能用于判断当前 Campaign 的预算、Bid、广告位、否词、暂停或放量。

## 生成脚本

标准化文件由以下脚本生成：

`scripts/ingest_rug_history_keywords.py`
