# Office Chair Category Traffic Data

## 类目

- 中文：办公椅 / 人体工程学办公椅
- 英文：office chair / ergonomic office chair / desk chair
- 类目标准化程度：半标品偏标品
- 用途：用于 `agents/category-traffic-strategy.md` 判断办公椅类目流量入口、头部集中度、竞对共用词和 L1-L5 流量层。

## 数据来源

### ABA / 类目词库

| 文件 | 原始来源 | sheet | 说明 |
|---|---|---|---|
| `raw/20260702_office_chair_ABA_keyword_library.xlsx` | `/Users/leo/Desktop/关键词库-办公椅.xlsx` | `aba-办公椅` | 办公椅、gaming chair、computer chair 三组 ABA 排名词 |
| `raw/20260702_office_chair_ABA_keyword_library.xlsx` | `/Users/leo/Desktop/关键词库-办公椅.xlsx` | `冷启动` | 冷启动关键词、冷启动概率、差异化词库 |

### 竞对关键词表

数据来源：紫鸟浏览器 / 西柚洞察关键词导出。

时间范围：`2026-06-24~2026-06-30`

| 竞品 ASIN | 文件 |
|---|---|
| `B0D9VPSQM7` | `raw/20260702_office_chair_competitor_B0D9VPSQM7_keywords.xlsx` |
| `B0DGTBNFRP` | `raw/20260702_office_chair_competitor_B0DGTBNFRP_keywords.xlsx` |
| `B0DPHLWNBG` | `raw/20260702_office_chair_competitor_B0DPHLWNBG_keywords.xlsx` |
| `B0FL7NTDGC` | `raw/20260702_office_chair_competitor_B0FL7NTDGC_keywords.xlsx` |
| `B0FXMJ6DDK` | `raw/20260702_office_chair_competitor_B0FXMJ6DDK_keywords.xlsx` |

## 标准化文件

| 文件 | 行数 | 说明 |
|---|---:|---|
| `normalized/20260702_office_chair_aba_keywords_normalized.csv` | 1,123 | ABA 关键词标准化，字段包含 `category`、`source_group`、`keyword`、`aba_rank` |
| `normalized/20260702_office_chair_cold_start_keywords_normalized.csv` | 706 | 冷启动关键词标准化，字段包含 `keyword`、`cold_start_probability`、`differentiation_note` |
| `normalized/20260702_office_chair_competitor_keywords_normalized.csv` | 7,490 | 5 个竞品 ASIN 原始关键词标准化 |
| `normalized/20260702_office_chair_competitor_keyword_coverage.csv` | 2,843 | 竞对关键词覆盖度聚合，字段包含 `competitor_asin_count`、`source_asins`、`total_traffic`、`best_aba_rank` |

## 当前可用性

- ABA 类目词库：可用。
- 冷启动词库：可用。
- 竞对词表：可用，覆盖 5 个 ASIN。
- Top3 点击份额、Top3 转化份额、Top3 ASIN：竞对关键词表中可用。
- 数据置信度：中高。

## 使用规则

1. 本数据只用于办公椅类目流量结构、入口数量、竞对共用词和 L1-L5 流量层判断。
2. 本数据可辅助新品办公椅选词，但不能替代具体产品属性匹配。
3. 本数据不能作为老品广告优化数据源，不能用来判断当前 Campaign 的预算、Bid、广告位、否词、暂停或放量。
4. 标品/半标品判断时，必须优先看 `competitor_keyword_coverage` 中的竞对覆盖 ASIN 数，再结合 ABA 排名判断流量层。
5. `gaming chair`、`chair`、品牌词、配件词、轮子/垫子/替换件词需要单独隔离，不得直接计入办公椅普通入口 `N_core`。

## 代表性竞对共用词

以下关键词在 5 个竞品 ASIN 中均出现，属于办公椅类目流量层判断的重点候选：

- `office chair`
- `desk chair`
- `gaming chair`
- `ergonomic office chair`
- `computer chair`
- `chair`
- `ergonomic chair`
- `office chairs`
- `office chair with foot rest`
- `ergonomic office chair with lumbar support`
- `mesh office chair`
