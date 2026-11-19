# Pet Water Fountain 类目

仅当当前类目是 `pet_water_fountain` 时使用本文件。

## V3 优先

对于 Amazon US cat/dog non-food / non-supplement / non-drug hardware/goods，包括符合这些条件的 pet water fountain，必须先走 `../../pet-listing-agent/AGENTS.md` V3。

命中 V3 时：

- 路由入口：`../../pet-listing-agent/AGENTS.md`
- 参考：`../../pet-listing-agent/CHANGES.md`、`../../pet-listing-agent/references/category-pet.md`、`../../pet-listing-agent/references/intake-template.md`、`../../pet-listing-agent/references/limits.md`
- 确定性验证：`../../pet-listing-agent/scripts/validate.py` 必须检查每一份实际生成的 draft；`tests/run_tests.py` 只运行测试套件，不能替代 draft 校验。按 package 文档中的确切 CLI 运行，不要自行发明 validator flags
- 输出固定顺序：`主标题 -> 亮点 -> 五点描述 -> 详情文案 -> 简要总结`
- 长度 gate：主标题 <= 75，亮点 <= 125，五点每条 <= 256 且合计 <= 1000，详情文案 <= 2000
- 只选 3-5 个 core keywords
- 旧的 `Title`、`Item Highlights`、`Bullet Points`、`Product Description`、`Search Terms` 输出格式不得覆盖 V3

以下情况不要自动 V3，也不要 fallback 到 `rug`：

- 非 Amazon US
- 非 cat / dog 物种
- food / supplement / drug / medicinal
- 无法确认商品性质

这些必须进入澄清 / `Needs manual confirmation`。

`pet-listing-agent` 包内若引用 `keyword-data-contract.md` 或 `knowledge-bases/pet`，未随包提供时不是数据源；实际关键词契约是 `../keyword-library-contract.md`，`knowledge-bases/pet` 仅在外部提供并显式挂载时可用。

## 旧 pet_water_fountain 兼容规则

以下内容作为 legacy `pet_water_fountain` 安全基线；只有 V3 不命中且已经用户澄清后，才允许进入本 legacy 流程。任何旧标题 / 输出规则与 V3 冲突时，V3 优先。

## 词库

使用：

- `amazon-listing-webapp/data/categoryKeywordData.json` -> `pet_water_fountain`

生成宠物喂水器 Listing 时，不能使用 rug 或 chair 关键词。

## 产品名

选择最准确的产品名：

- `Pet Water Fountain`
- `Dog Water Fountain`
- `Cat Water Fountain`
- `Pet Water Dispenser`
- 其他用户确认的宠物喂水产品名

## 路由触发词

出现这些信息时走本类目：

- pet water fountain、dog water fountain、cat water fountain
- pet water dispenser、dog water dispenser、cat water dispenser
- dog water bowl、cat water bowl
- filter、pump、spout、stainless steel fountain
- wireless、cordless、battery、sensor flow
- 宠物喂食 / 喂水上下文

## 关键词处理

- dog / cat / pet ABA 行只是流量候选，不是自动文案。
- 产品不是对应配件时，排除 filter-only、mat-only、bottle-only、feeder-only、pump-only 等纯配件词。
- 移除竞品品牌和 ASIN。
- dog / cat 适配对象只有在用户确认时才能写。
- 容量、不锈钢、无线、cordless、电池、过滤、泵、出水口、感应、静音、续航、清洁方式，只有确认后才能写。

## Title 格式

推荐结构：

`Brand Size/Spec Core Product, Material/Feature Dog Cat Pet Fountain`

已确认时，Title 可放这些简短属性：

- 容量，如 `5L` 或 `10L`
- Stainless Steel
- Wireless
- Cordless
- Filter
- Pump
- Spout
- Dog Cat
- 适配宠物类型

## 五点主题

1. 产品身份、容量 / 规格、宠物类型、喂水用途。
2. 材质、碗、出水口、泵、过滤、出水结构，只写确认内容。
3. 供电方式，如 wireless、cordless、battery、sensor flow、plug-in，只写确认内容。
4. 清洁、加水、滤棉 / 滤芯更换、日常维护，只写有依据内容。
5. 包装清单、适配对象、需人工确认事项，不写医疗、抗菌、健康水、兽医推荐、安全保证、排名声明。

## 高风险声明

没有正式证明且平台允许时，不要写：

- 抗菌 / 杀菌 / 除菌类声明。
- 疾病预防或治疗声明。
- 健康水、保证饮水类声明。
- 兽医推荐。
- Non-toxic、BPA free、food grade、small-animal-safe。
- Waterproof 或 outdoor-use。

## 需证明 / 慎用项

这些需要产品证据，或者必须标记为需确认：

- `304 stainless steel`
- 电池容量，如 `4000mAh`
- 续航，如 `15-25 days`
- 静音 / silent
- Sensor-activated water flow
- Dishwasher-safe cleaning
- 精确泵性能或过滤性能

推荐谨慎表达：

- `supports about 15-25 days depending on mode, frequency, pet traffic, and environment`
- `helps catch visible hair and debris`
- `routine washing`
- `low-noise operation`

不要写绝对化结果。
