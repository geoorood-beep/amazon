# Rug ABA 关键词库固定数据源

更新时间：2026-07-07

版本生命周期：

- `generated_at`: `2026-07-07`
- `effective_from`: `2026-07-07`
- `expires_at`: `null`（未设置固定失效日；源哈希变化时立即失效）
- `superseded_by`: `null`
- `lifecycle_status`: `ACTIVE_REFERENCE`

本目录替代旧默认地毯通用 ABA 表 `reference/通用地毯类目ABA关键词库_202605_v2.xlsx`，作为 Rug 新品推广、地毯新广告搭建和 ABA 选词的默认数据源。

## 固定文件

| 类目 / 场景 | 文件 | 必读 sheet | 有效行数 | 说明 |
|---|---|---|---:|---|
| Area Rug / 区域 / 长条 / 室内进门垫 / 圆形 | [打开 Area Rug ABA](area_rug_ABA关键词库_202605_v8.xlsx) | `广告词库` | 3212 | 默认主库，覆盖 area rug、runner、entryway、round 等类型 |
| Bathroom Rugs / 浴室垫 | [打开 Bathroom ABA](bathroom_rugs_ABA关键词库_202605.xlsx) | `广告词库` | 985 | 浴室地垫、淋浴浴缸垫、马桶轮廓垫、浴室长条、浴室套装 |
| Kitchen Rugs / 厨房垫 | [打开 Kitchen ABA](kitchen_rugs_ABA关键词库_202605_v2.xlsx) | `广告词库` | 331 | 厨房垫、under sink、anti fatigue 等厨房场景 |
| Outdoor Rug / 户外地毯 | [打开 Outdoor ABA](outdoor_rug_ABA关键词库_202605_v2.xlsx) | `广告词库` | 1223 | outdoor 区域和长条场景 |

## 来源哈希

| 文件 | SHA-256 |
|---|---|
| `area_rug_ABA关键词库_202605_v8.xlsx` | `07f51899cc947609fe88eace72e3136278b7ce2cfa8b7d4247eadd5d914fde36` |
| `bathroom_rugs_ABA关键词库_202605.xlsx` | `aac64ea8043eaa5ceefc8992c4ab80ae14b8a554d69d5787a868d8b994437aa8` |
| `kitchen_rugs_ABA关键词库_202605_v2.xlsx` | `b74a1202a0f7dd7b2a33b16b1cdb6e560522ab64e2f2bd5d4d69917ced872be6` |
| `outdoor_rug_ABA关键词库_202605_v2.xlsx` | `a5f0a55ce817c50a3b385f43e3e0c349069cb7bc7a7bccda1e6a23ea9cb99a15` |

每次读取前校验文件哈希。任一哈希变化时，将本映射标记为 `STALE_REBUILD_REQUIRED`，重新生成后更新 `generated_at/effective_from/source_hash`，不得沿用旧映射继续给出高置信结论。

上一层：[数据源目录](../../knowledge/README.md)、[新品规则](../../rules/domains/new-product/README.md)、[类目流量规则](../../rules/domains/category-traffic/README.md)。

## 读取规则

- 调用 Rug ABA 关键词库时，只读取每个文件的 `广告词库` sheet。
- 不读取、不合并、不参考 `说明`、`汇总`、`Listing词库`、`否定禁用`、`类型_*` 等其他 sheet，除非用户明确要求检查源表结构。
- 旧通用表仅作为历史备份，不再作为默认地毯 ABA 调用入口。
- 四个文件之间按产品场景和地毯区域选择，不得把所有词混成一个无场景全量池。
- 需要跨文件合并历史效果证据时，同词采用保守冲突策略：任一来源不是 `合规状态=安全` 或 `广告状态=可投`，以及地毯类型、层级、相关度等字段不一致时，统一进入隔离复核；不得随机选择一个来源覆盖冲突。

## 必读字段

四个文件的 `广告词库` 均包含以下核心字段：

- `搜索词`
- `搜索量排名`
- `规范词根`
- 类目判断字段：`类目判断` 或以类目命名的 `*类目判断`
- `地毯类型`
- `详细分类`
- `推荐层级`
- `相关度等级`
- `合规状态`
- `Listing状态`
- `广告状态`
- `综合优先级`
- `广告用途`
- `否定/隔离类型`
- `尺寸标签`
- `场景标签`
- `功能标签`
- `风格图案标签`
- `颜色标签`
- `材质结构标签`
- `形状标签`
- `人群宠物标签`
- `判断原因`
- `来源文件`
