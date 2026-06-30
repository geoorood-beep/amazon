# 类目历史出单词数据目录

本目录用于存放不同类目的历史出单搜索词数据。

目录规则：

- 每个类目单独建文件夹。
- `raw/` 保存原始报表，不改字段、不覆盖。
- `normalized/` 保存标准化后的历史出单词表。
- `metadata.md` 记录数据来源、时间范围、适用边界和缺失字段。

当前推荐类目目录：

- `pet_water_fountain/`
- `rug/`

当前已固定数据：

| 类目 | 当前标准化文件 | 状态 |
|---|---|---|
| `pet_water_fountain` | `pet_water_fountain/normalized/20260629_pet_water_fountain_historical_search_terms_normalized.xlsx` | 已入库：10L / 5L 无线不锈钢喂水器历史搜索词 |

详细入库、字段和调用规则见：

`/Users/leo/Documents/广告智能体 2/agents/category-history-data.md`
