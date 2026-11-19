# 类目路由

类目路由决定可以调用哪一套关键词库和风险库。必须在关键词评分和文案生成之前完成。

## Amazon US pet hardware/goods V3 优先路由

在进入任何旧 Amazon 类目路由 / 生成流程之前，先判断是否同时满足：

- 平台：Amazon US
- 物种：cat 或 dog
- 商品性质：non-food、non-supplement、non-drug 的 hardware/goods

命中时，必须路由到：

- `../pet-listing-agent/AGENTS.md`
- `../pet-listing-agent/CHANGES.md`
- `../pet-listing-agent/references/category-pet.md`
- `../pet-listing-agent/references/intake-template.md`
- `../pet-listing-agent/references/limits.md`
- 确定性验证：`../pet-listing-agent/scripts/validate.py` 必须检查每一份实际生成的 draft；`tests/run_tests.py` 只运行测试套件，不能替代 draft 校验。按 package 文档中的确切 CLI 运行
- 不要自行发明 validator flags

V3 输出固定顺序为：`主标题 -> 亮点 -> 五点描述 -> 详情文案 -> 简要总结`。

关键词只选 3-5 个 core keywords。

硬性 gate：

- 主标题 <= 75 characters
- 亮点 <= 125 characters
- 五点描述每条 <= 256 characters，五点合计 <= 1000 characters
- 详情文案 <= 2000 characters

此优先级高于下面 `rug` / `chair` / `pet_water_fountain` 的 legacy 路由。

对于已经识别或疑似 pet 商品的 scoped task，以下情况不要自动套 V3，也不要 fallback 到 `rug`：

- 非 Amazon US 站点
- 非 cat / dog 物种，例如 small animal / bird / reptile / fish 等
- food / supplement / drug / medicinal pet products
- 无法确认商品性质是否属于 non-food hardware/goods

这些情况应进入澄清 / `Needs manual confirmation`；如果后来确认不命中 V3，再按旧流程处理。非 pet 的 legacy `rug` / `chair` 等任务保持原有流程不变。

## 代码入口

- `amazon-listing-webapp/lib/categoryKeywordRouting.ts`
- `amazon-listing-webapp/app/api/generate/route.ts`
- `amazon-listing-webapp/data/categoryKeywordData.json`

`resolveCategoryKeywordData()` 应从 `categoryKeywordData.json` 中选择类目专用词库。只有找不到类目库时，才使用 fallback 数据。

## 支持类目

### `pet_hardware_goods_v3`

文档分发标签，不是旧 app 实现的运行时类目；仅 Amazon US cat/dog non-food / non-supplement / non-drug hardware/goods。入口和限制见上。

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

若该产品同时满足 Amazon US cat/dog non-food / non-supplement / non-drug hardware/goods，V3 优先于本 legacy 类目。

## 路由优先级

0. 先判断是否命中 Amazon US cat/dog non-food / non-supplement / non-drug hardware/goods；命中则路由 V3 包。
1. 如果表单或用户显式给了有效类目，优先使用。
2. 否则从产品类型和运营备注推断。
3. 产品类型词优先于泛功能词。
4. 如果无法可靠判断类目，因历史兜底是 rug，可以暂时默认 `rug`，但必须把 `productCategory` 写入需人工确认。疑似 pet 商品不得自动默认 `rug`；必须先澄清平台、物种和商品性质。

## 隔离规则

- V3 只使用 `pet-listing-agent` 的规则和验证；不随包提供自有 V3 词库，也不得把旧 `rug` / `chair` / 与当前产品不匹配的 `pet_water_fountain` 高流量词接入 V3。用户显式提供且与当前产品匹配的 `pet_water_fountain` 词库 / 产品证据，可按同目录 `keyword-library-contract.md` 和 V3 规则使用。
- Rug 生成只能使用 `rug` 关键词和风险数据。
- Chair 生成只能使用 `chair` 关键词和风险数据。
- Pet water fountain legacy 生成只能使用 `pet_water_fountain` 关键词和风险数据。
- 不能为了提高埋词率，从别的类目拿高流量词。
- 被排除或被屏蔽的关键词，不能计入埋词覆盖率。

## Pet V3 包缺失引用

`pet-listing-agent` 包中若引用 `keyword-data-contract.md` 或 `knowledge-bases/pet`，这些文件未随包提供。实际关键词 / 风险契约在本仓库同目录 `keyword-library-contract.md`；`knowledge-bases/pet` 或用户显式提供的 product-matching pet 词库只有在带产品证据并符合 V3 契约时才可用。不得虚构或声称缺失数据已存在。

## 新增类目的步骤

要新增类目时：

1. 在 `categoryKeywordData.json` 中添加新的类目 key。
2. 在 `categoryKeywordRouting.ts` 中添加标准化和推断逻辑。
3. 在 `localListingGenerator.ts` 中添加产品名 / Title 逻辑。
4. 只有类目确实需要时，才新增或收紧 audit 规则。
5. 新建 `agents/categories/<new-category>.md`。
6. 用至少 1 个代表产品验证生成和审核。

`pet_hardware_goods_v3` 是独立 package 类目，不由旧 `categoryKeywordData.json` 驱动；本次更新保持该 package 不变，不要为 V3 在旧 app 中创建 `categoryKeywordData` 条目。
