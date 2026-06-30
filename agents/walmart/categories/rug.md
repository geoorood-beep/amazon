# Walmart Rug 类目

这是当前 `$walmart-listing-generator` skill 已经沉淀最完整的类目。

## 必用知识库

当前 skill 使用：

- `assets/walmart_listing_knowledge_base.xlsx`
- `references/rules.md`
- `scripts/walmart_kb.py`

在多类目架构中，rug 应对应：

`category_libraries/rug/walmart_listing_knowledge_base.xlsx`

## Size 决策

每个 supplied size 都必须有 type decision。

Runner size：

- `2x6`
- `2x8`
- `2x10`
- `2x12`
- `2.5x8`
- `3x8`
- `3x10`

Area rug size：

- `5x7`
- `6x9`
- `8x10`
- `9x12`
- 以及类似常规房间尺寸

Accent / entryway size：

- `2x3`
- `3x5`
- 以及门口 / 玄关小尺寸

## Runner 规则

Runner、hallway runner、kitchen runner、entryway runner 只能用于：

- 已确认 runner size。
- 或当前产品有明确 runner 证据。

不能把 runner 词用于非 runner size。

## Area Rug Title 规则

对 `5x7`、`6x9`、`8x10`、`9x12` 等 area rug：

- 当前产品支持 living room placement 且风险扫描允许时，Product Title 优先使用 `rug for living room`。
- 不适用于 runner size 或 doorway-focused accent size。
- 当 Title 仍有空间且支持室内房间场景时，在后部加入 `Home Office` 等额外场景。
- 不要让 area-size title 只停在 `Bedroom`，如果还能放更宽场景。

## Title 文案规则

- Product Title 10-199 characters，目标 120-180。
- 保持 Proper Capitalization。
- `KUETH` 和 `DEORAB` 保持全大写。
- 颜色只写主要可见颜色。
- 详细颜色组合放 Description 或 Key Features。
- 图案 / 风格短语中，优先用 `Rug`，不要为了减少 `Rug` 重复写成 `Design`。
- 例：写 `Pink Bow Rug`，不要写 `Pink Bow Design`。

## Description 规则

- 英文一段，80-150 words。
- 避免 `it`、`its` 这类模糊代词指代产品。
- 重复搜索相关 noun phrase，如 `the washable rug`、`the area rug`、`the runner rug`、`the KUETH rug`。
- 有当前证据时，可写 `homes with pets`、`busy households with pets`、`family living spaces`。

## Key Features 规则

- 默认 5 条，允许 3-10 条。
- 每条 180-280 characters。
- 每条格式：`Short Benefit Title: buyer-value sentence`。
- Machine Washable、Low Pile、backing、softness、pet-household claims 必须有当前证据。
- 不写 absolute safety、health、stain-proof、waterproof、antibacterial、damage-prevention claims。
