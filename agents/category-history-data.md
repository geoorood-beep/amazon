# AGENT: 类目历史出单词数据管理

本 AGENT 用于沉淀、读取和调用不同类目的历史出单搜索词数据。它只服务“选词中的历史数据参考”、同类可复用词推荐、新品或新广告候选词补充。

本 AGENT 不是老品推广方案的数据源报表，不能替代当前链接 / 当前 Campaign / 当前广告组的真实搜索词、广告位、预算、Bid、商品表现或趋势报表。

当新品推广、新广告搭建、搜索词选词复用任务需要“同类历史成交证据”时，必须先读取本 AGENT，确认是否存在可用的类目历史出单词数据。

## 固定存放路径

类目历史出单词数据固定放在：

`/Users/leo/Documents/广告智能体 2/reference/category-history/`

每个类目单独建文件夹，不同类目的历史数据不能混放。

推荐目录：

| 类目 | 目录名 | 说明 |
|---|---|---|
| 宠物喂水器 | `pet_water_fountain/` | 猫狗饮水机、无线喂水器、不锈钢喂水器等 |
| 地毯 | `rug/` | area rug、runner rug、doormat、bathroom rugs、kitchen rugs 等 |
| 其他类目 | 英文小写下划线 | 例如 `chair/`、`storage_bag/`，按实际产品建立 |

类目目录下建议保留：

- `raw/`：用户原始报表，不改字段、不覆盖。
- `normalized/`：标准化后的历史出单词表。
- `metadata.md`：类目说明、数据来源、时间范围、适用边界。

当前已固定数据：

| 类目 | 标准化文件 | 数据来源 | 使用边界 |
|---|---|---|---|
| `pet_water_fountain` | `reference/category-history/pet_water_fountain/normalized/20260629_pet_water_fountain_historical_search_terms_normalized.xlsx` | 10L / 5L 无线不锈钢喂水器历史搜索词 | 只做喂水器类目选词参考 |
| `rug` | `reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx` | 冬豚 / 岚风 Rug 关键词分析汇总，905 条出单词明细，818 个聚合词 | 只做 Rug 新品选词、新广告候选词和搜索词复用参考；不得替代当前链接真实报表 |

## 标准文件命名

原始文件命名：

`raw/YYYYMMDD_类目_来源_搜索词报表.xlsx`

标准化文件命名：

`normalized/YYYYMMDD_类目_historical_search_terms_normalized.xlsx`

如果同一类目有多个来源，可以按账号、站点、品牌或产品线拆分：

`normalized/YYYYMMDD_pet_water_fountain_US_accountA_normalized.xlsx`

## 标准字段

标准化表必须尽量包含以下字段。字段不足时不能补造，只能标记缺失。

| 字段 | 必填 | 说明 |
|---|---|---|
| `category` | 是 | 类目，如 `pet_water_fountain`、`rug` |
| `subcategory` | 否 | 子类目或产品类型，如 `10L stainless wireless`、`runner rug` |
| `source_product` | 否 | 来源产品名称或父体 |
| `source_asin` | 否 | 来源 ASIN，可为空 |
| `source_sku` | 否 | 来源 SKU，可为空 |
| `date_start` | 条件必填 | 报表开始日期；没有日期时写空 |
| `date_end` | 条件必填 | 报表结束日期；没有日期时写空 |
| `search_term` | 是 | 用户实际搜索词 |
| `campaign` | 否 | 原始广告活动 |
| `ad_group` | 否 | 原始广告组 |
| `match_type` | 否 | Broad / Phrase / Exact / Auto |
| `targeting` | 否 | 原投放词、ASIN 或类目 |
| `clicks` | 是 | 点击 |
| `spend` | 是 | 广告花费 |
| `ad_orders` | 是 | 广告订单 |
| `direct_orders` | 否 | 直接订单，源表没有则留空 |
| `sales` | 否 | 广告销售额 |
| `acos` | 否 | ACOS，源表没有可由 spend / sales 计算 |
| `cvr` | 否 | CVR，源表没有可由 ad_orders / clicks 计算 |
| `cpa` | 否 | CPA，源表没有可由 spend / ad_orders 计算 |
| `currency` | 否 | 币种 |
| `source_file` | 是 | 原始文件名 |
| `data_confidence` | 是 | 高 / 中 / 低 |
| `notes` | 否 | 缺失字段、异常、人工备注 |

最低可用字段：

- `search_term`
- `clicks`
- `spend`
- `ad_orders`
- `source_file`

缺少 `ad_orders` 的表不能作为历史出单词数据，只能作为搜索词观察数据。

## 字段同义映射

导入 Amazon 报表时，常见字段按以下方式映射：

| 原始字段 | 标准字段 |
|---|---|
| `Customer Search Term` / `Search Term` / `搜索词` | `search_term` |
| `Campaign Name` / `Campaign` / `广告活动` | `campaign` |
| `Ad Group Name` / `Ad Group` / `广告组` | `ad_group` |
| `Match Type` / `匹配类型` | `match_type` |
| `Targeting` / `Keyword` / `投放词` | `targeting` |
| `Clicks` / `点击` | `clicks` |
| `Spend` / `Cost` / `花费` | `spend` |
| `7 Day Total Orders` / `Orders` / `广告订单` | `ad_orders` |
| `7 Day Total Sales` / `Sales` / `销售额` | `sales` |
| `ACOS` / `Advertising Cost of Sales` | `acos` |

字段名不一致时，先做字段映射，再进入新品或搜索词判断。不得因为字段名不同就直接判定数据不可用。

## 数据有效性规则

导入前按顺序检查：

1. 类目是否明确。类目不明确时不能入库，只能放入待确认。
2. 日期范围是否明确。没有日期时，不能判断近 3 天、7 天、14 天趋势。
3. 搜索词是否为用户实际搜索词，不是广告投放词。
4. `clicks`、`spend`、`ad_orders` 是否为数值。
5. `ad_orders > 0` 的行才是历史出单词。
6. 同一搜索词如果来自多个广告组，不要直接丢失原始行；可以另建聚合表，但必须保留 raw。
7. 不同类目、不同产品形态不能混算。例如 `pet_water_fountain` 不能和 `pet_food_bowl` 混为一个类目。

数据置信度：

- 高：有日期、Campaign、Ad Group、点击、花费、订单、销售额，且时间范围明确。
- 中：有搜索词、点击、花费、订单，但缺少日期或广告组。
- 低：只有搜索词和订单，或来源无法确认。低置信度只能辅助参考，不能作为放量依据。

## 新品推广调用规则

新品推广任务读取历史类目数据时，按以下顺序：

1. 先匹配当前产品类目和产品形态。
2. 再筛选与当前产品属性相关的历史出单词。
3. 历史出单词优先级高于通用 ABA 词，但必须经过 ABA 阶段和产品匹配校验。
4. 历史出单词不能直接变成当前新品的 CPA / CVR / ACOS 阈值，只能作为同类参考。
5. 当前新品没有自己的稳定数据时，不得用历史类目 ACOS 直接判定暂停或否词。
6. 如果历史词与当前产品属性冲突，即使历史出单，也不能投。
7. Rug 类目调用 `reference/category-history/rug/` 时，必须继续执行 `agents/new-product-promotion.md` 中的地毯区域、尺寸、风格、颜色、材质和 `图案动物类型` 强匹配规则。

新品调用结论必须写清：

- 是否找到同类历史数据。
- 使用了哪个类目目录和哪个标准化文件。
- 历史数据置信度。
- 哪些词是“历史出单词来源”，哪些词只是“ABA 来源”。

没有可用历史数据时，必须写：

`未找到可用类目历史出单词数据，本次按 ABA + 产品属性匹配 + 新品低预算验证处理。`

## 选词复用调用规则

类目历史数据在任何任务中都只用于选词参考，不作为老品优化方案的数据源报表。

允许使用：

1. 新品推广选词时，作为同类历史成交证据。
2. 新广告搭建时，作为可复用投放词池和词根方向。
3. 搜索词再投放时，作为跨产品的词根补充和 ABA 匹配方向。
4. 老品需要“新增候选词 / 新广告架构”时，只作为选词参考。

禁止使用：

1. 不得作为老品推广诊断的数据源报表。
2. 不得用来判断当前老品 Campaign 的预算是否合理。
3. 不得用来判断当前老品 Bid、广告位 TOS / ROS / PP、时段节奏、趋势好坏。
4. 不得用来决定当前老品暂停、降预算、否词、放量或广告位调整。
5. 不得覆盖当前链接自己的 ACOS、CPA、CVR、点击、订单、花费和趋势。

老品推广或搜索词再投放任务中，当前链接自己的搜索词数据优先级最高。没有当前链接真实报表时，必须标记“缺少老品诊断源数据”，只能输出选词参考，不能输出老品优化动作。

用于当前链接搜索词再投放时，仍需读取 `agents/search-term-reinvestment.md`，并以当前链接搜索词报表作为源数据。

## 类目隔离规则

不同类目历史词不得直接互相调用。

允许调用：

- `10L 不锈钢无线猫狗通用喂水器` 调用 `pet_water_fountain` 历史词。
- `2x6 runner rug` 调用 `rug/runner rug` 历史词。
- `8x10 area rug` 调用 `rug/area rug` 历史词。

禁止调用：

- 喂水器调用地毯历史词。
- 地毯调用喂水器历史词。
- 猫砂盆、宠物碗、宠物垫调用喂水器历史词，除非用户明确说明为同一产品线且可参考。
- 地毯下的 `bathroom rugs` 直接套用 `runner rug` 历史词，除非词本身和当前产品形态匹配。

## 入库动作要求

当用户提供新的历史搜索词或出单词表，并要求固定到项目中时：

1. 先判断类目目录是否存在，不存在则创建。
2. 原始文件复制或保留到 `raw/`，不得覆盖旧文件。
3. 生成标准化表到 `normalized/`。
4. 写入或更新该类目的 `metadata.md`。
5. 在回答中说明：入库类目、原始文件、标准化文件、日期范围、数据置信度、缺失字段。

如果用户只是临时提供数据用于本次分析，但没有要求固定，不要擅自入库。

## 判断禁区

- 不要把 ABA 表当作历史出单词表。
- 不要把点击无单词当作历史出单词。
- 不要把不同类目的历史词混成一个“通用历史词库”。
- 不要用历史类目数据直接替代当前链接数据。
- 不要把类目历史数据作为老品推广方案的数据源报表。
- 不要用类目历史数据判断老品预算、Bid、广告位、趋势、暂停或放量动作。
- 不要因为某词在历史类目出过单，就跳过产品相关性和合规检查。
- 不要在缺少日期字段时判断近 3 天、7 天、14 天趋势。
