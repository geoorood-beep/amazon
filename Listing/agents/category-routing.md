# 类目路由

类目路由决定可以调用哪一套关键词库和风险库。必须在关键词评分和文案生成之前完成。

## 代码入口

- `amazon-listing-webapp/lib/categoryKeywordRouting.ts`
- `amazon-listing-webapp/app/api/generate/route.ts`
- `amazon-listing-webapp/data/categoryKeywordData.json`

`resolveCategoryKeywordData()` 应从 `categoryKeywordData.json` 中选择类目专用词库。只有找不到类目库时，才使用 fallback 数据。

## 支持类目

### `rug`

出现这些信息时走 rug：

- rug、area rug、runner rug、washable rug、door mat、doormat、entryway rug
- 地毯常见尺寸，同时产品类型也支持地毯判断
- 地毯属性，如 low pile、non slip backing、washable、TPR backing、hallway runner

### `chair`

出现这些信息时走 chair：

- chair、office chair、desk chair、ergonomic chair、executive chair
- gaming chair、computer chair、video chair
- criss cross chair、cross legged chair
- MINILIVE、W09、W703、椅子 ASIN / SKU 上下文

### `pet_water_fountain`

出现这些信息时走 pet_water_fountain：

- pet water fountain、dog water fountain、cat water fountain
- pet water dispenser、dog water dispenser、cat water dispenser
- dog water bowl、cat water bowl
- filter、pump、spout、stainless steel fountain、wireless / cordless fountain
- 宠物喂食 / 喂水上下文

## 路由优先级

1. 如果表单或用户显式给了有效类目，优先使用。
2. 否则从产品类型和运营备注推断。
3. 产品类型词优先于泛功能词。
4. 如果无法可靠判断类目，因历史兜底是 rug，可以暂时默认 `rug`，但必须把 `productCategory` 写入需人工确认。

## 隔离规则

- Rug 生成只能使用 `rug` 关键词和风险数据。
- Chair 生成只能使用 `chair` 关键词和风险数据。
- Pet water fountain 生成只能使用 `pet_water_fountain` 关键词和风险数据。
- 不能为了提高埋词率，从别的类目拿高流量词。
- 被排除或被屏蔽的关键词，不能计入埋词覆盖率。

## 新增类目的步骤

要新增类目时：

1. 在 `categoryKeywordData.json` 中添加新的类目 key。
2. 在 `categoryKeywordRouting.ts` 中添加标准化和推断逻辑。
3. 在 `localListingGenerator.ts` 中添加产品名 / Title 逻辑。
4. 只有类目确实需要时，才新增或收紧 audit 规则。
5. 新建 `agents/categories/<new-category>.md`。
6. 用至少 1 个代表产品验证生成和审核。
