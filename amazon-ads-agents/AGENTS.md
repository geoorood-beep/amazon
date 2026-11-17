# UTA-amazon-ads V1.4

系统名称：`UTA-amazon-ads`。对外说明、输出方案、版本记录统一使用此名称；`lulu` 只是广告组命名中的运营名，不得当作系统名。

**Grok 的唯一入口是 `GROK.md`**（定品类、任务判断、必读顺序、复述校验、三类任务步骤、禁区）。修改本文件或任何子 AGENT 后，如影响 Grok 的流程或版本号，必须同步更新 `GROK.md`，并按 `GROK.md` 末尾“给维护者”升级版本号、在 `VERSION.md` 写“Grok 须知”。Grok 每次从 `main` 读最新版，所以推送到 `main` 即对 Grok 生效。

本项目使用“一个总入口 + 多个子 AGENTS”的结构。总入口只负责路由；具体判断规则放在 `agents/` 子文件，避免单个 AGENTS 过长导致读取不完整。

当前版本：`V1.4`（见 `VERSION.md`）

## 三层架构（V1.3 起）

| 层 | 位置 | 内容 | 换品类时 |
|---|---|---|---|
| 通用规则 | `agents/` | 老品诊断、新品架构、搜索词复投、输出模板、Grok 操作、知识融合规则 | 不动 |
| 通用知识 | `knowledge/ads-framework/` | 广告方法论：【标准】`standards/`、【建议】`suggestions.md`、【待补】`pending.md`、负责人口径 `decisions/` | 不动 |
| 品类层 | `categories/<品类>/` | 品类卡、阈值、引擎配置、品类知识、运营数据仓 | 每个品类一份 |

品类注册表：`categories/README.md`（已开通 / 知识中 / 待建）。任何任务先确定品类；品类状态不是“已开通”时只给通用规则建议，不出执行指令单。不同品类的阈值、品牌词、准词表不得互相借用。

V1.3 新增内容：多品类架构 `categories/`（喂水器已开通，喂食器、智能猫厕所占位）；课程知识分解为通用方法论 `knowledge/ads-framework/`；宠物用品知识库并入；引擎按 `--category` 读取品类配置。

V1.2 新增内容：Grok 云端电脑操作员、`ops/` 运营数据仓与数据成熟度、喂水器老品规则引擎 `old_product_module/`、目标 CPA 与竞价上限按历史数据自动推导、品牌词 meandu / pokpet 保护。

V1.1 固定内容：广告组统一命名、CPA 正常线上限预算、Rug 输入模板和动物图案强匹配、Rug 历史出单词库、Rug 高流量核心隔离否词、老品出单词跨广告产品拓量。

## AGENTS 目录

当用户输入 `AGENTS 目录` 时，必须读取并展示：

`agents/agents-directory.md`

展示时要说明每个 AGENT 能带来什么结果、用户需要输入什么、需要维护什么基础数据、缺失数据会造成什么影响。

新增、删除、改名或调整任何 AGENT 时，必须同步更新 `agents/agents-directory.md`。

## 读取顺序

处理任何亚马逊广告、新品推广、老品推广、搜索词、词根、ABA、类目流量结构、广告位、预算、Bid、否词或新广告搭建任务时，先读本文件，再按任务读取对应子 AGENTS：

1. 新品推广选词与广告架构搭建：读 `agents/new-product-promotion.md`
2. 老品推广总诊断：读 `agents/old-product-promotion.md`
3. 搜索词再投放 / 词根聚合 / ABA 匹配：读 `agents/search-term-reinvestment.md`
4. ABA 类目流量结构与打法判断：读 `agents/category-traffic-strategy.md`
5. 类目历史出单词数据管理：读 `agents/category-history-data.md`
6. 品类阈值标准：已注册品类读 `categories/<品类>/thresholds.md`；通用用法和地毯阈值读 `agents/category data thresholds.md`
7. 输出表格、老广告优化、新广告设置：读 `agents/promo-output-templates.md`
8. Grok 云端电脑取数、补数、照执行指令单在领星操作：读 `agents/grok-operator.md`
9. 三层知识的优先级、冲突裁决和每周综合判断流程：读 `agents/knowledge-base.md`。**任何品类的诊断、选词、架构或方案任务都必须同时读它**，并按需读 `knowledge/ads-framework/standards/` 中相关规则。
10. 品类信息（品牌词、竞品词、型号、负责人口径、开通状态）：读 `categories/README.md` 和 `categories/<品类>/category.md`。

如果任务同时涉及多个模块，按上面顺序合并判断。新品推广和老品推广先判断数据阶段，再选择对应 AGENT。搜索词再投放规则是老品推广 SOP 的子模块，不是总入口。只用 ABA 判断类目流量结构或打法时，先读 `agents/category-traffic-strategy.md`；如果要进一步判断某个具体产品如何投放，再进入新品推广或搜索词模块。

## 运营数据仓（GitHub 累积）

Grok 每周把领星报表、产品档案、缺失项、执行日志累积到 `categories/<类目>/ops/`，GitHub 提交历史即数据历史。已开通品类见 `categories/README.md`。

分析方处理某类目老品方案时，先读 `categories/<类目>/ops/README.md` 的 `当前成熟度` 和最新一条 `handoff.md`，只输出当前成熟度允许的动作。先运行 `old_product_module/cli.py --category <类目>` 生成方案草稿（否词、竞价、广告位、预算、加词的数字以引擎结果为准，不得自行改数），分析方再复核搜索词相关性、补充引擎未覆盖的广告商品层和跨广告产品判断；方案报告和执行指令单草稿放进 `categories/<类目>/ops/weekly/<周>/plan/`，执行指令单格式按 `categories/<类目>/ops/templates/execution-order-template.md`。`ops/` 下的数据是当前链接真实报表，可作为老品诊断数据源；`reference/category-history/` 仍只做选词参考。

## 默认数据源

默认喂水器 ABA 排名表：

`/Users/leo/Documents/广告智能体 2/reference/ABA喂水器.xlsx`

默认 Rug / 地毯 ABA 关键词库：

`/Users/leo/Documents/广告智能体 2/reference/rug-aba/`

固定文件为 `area_rug_ABA关键词库_202605_v8.xlsx`、`bathroom_rugs_ABA关键词库_202605.xlsx`、`kitchen_rugs_ABA关键词库_202605_v2.xlsx`、`outdoor_rug_ABA关键词库_202605_v2.xlsx`。调用时只读取每个文件的 `广告词库` sheet；旧 `reference/通用地毯类目ABA关键词库_202605_v2.xlsx` 仅作历史备份，不再作为默认地毯 ABA 调用入口。

当地毯新品推广任务只提供产品信息、历史搜索词或出单词表，且没有提供新的 ABA 表时，默认使用 `reference/rug-aba/` 下对应场景文件。不同地毯类型必须按 `agents/new-product-promotion.md` 中的文件映射读取，不要混用同一个 ABA 池。

用户当前任务提供新的 ABA 表时，以新 ABA 表优先。

类目历史出单词数据固定目录：

`/Users/leo/Documents/广告智能体 2/reference/category-history/`

已固定类目历史出单词数据：

- 地毯 / Rug：`reference/category-history/rug/`
- 宠物喂水器：`reference/category-history/pet_water_fountain/`

类目流量结构数据固定目录：

`/Users/leo/Documents/广告智能体 2/reference/category-traffic/`

已固定类目流量数据：

- 办公椅 / 人体工程学办公椅：`reference/category-traffic/office_chair/`

当用户提供历史搜索词、历史出单词、同类历史数据，或任务需要判断“同类历史成交证据”时，读取 `agents/category-history-data.md`。ABA 表和历史出单词表必须分开管理，不能把 ABA 词库当作历史出单词数据。

类目历史出单词数据只用于选词中的历史参考、同类可复用词推荐和新品/新广告候选词补充。它不是老品推广方案的数据源报表。老品推广诊断、预算、Bid、广告位、否词、暂停、放量等动作，必须使用当前链接 / 当前 Campaign / 当前广告组的真实报表。

## 总原则

- 不要只看 ACOS 直接调预算、Bid、暂停或放量。
- 先判断数据有效性、样本量、观察周期、对象映射，再给动作。
- 输出必须说明：观察周期、核心指标、命中规则、数据充分度、为什么没有选择其他动作。
- 新品或老品广告架构输出必须在第一张核心表下方追加 `判断依据与设计逻辑` 自然段，并用来源标签标明判断来自哪里：`【流量结构打法】`、`【历史数据】`、`【用户固定规则】`、`【ABA/产品属性】`、`【当前报表】`、`【人工输入/预算目标】`、`【缺失数据】`。不要另加表格或 sheet。
- 广告组命名必须采用 `SPU-广告产品-定向维度-匹配方式-场景分类-尺寸-运营名`。若方案由智能体输出，运营名统一写 `lulu`；若人工运营名已明确，则使用人工运营名。
- 单关键词广告组且 ABA 排名可确认时，定向维度后用括号写大致排名，例如 `runner rug(4k)`、`area rug(1.8w)`。千用 `k`，万用 `w`。多个词、词根、类目、Auto 或 ASIN 定向不得在广告组名称中写 ABA 排名。
- 广告组标准最低日预算按对应类目 / 型号 / 尺寸的 CPA 正常线上限设置；不同类目根据各自阈值、产品名称、场景、尺寸和运营名切换参考数据。预算低于 CPA 正常线上限时，只能定义为观察预算或拓词预算，不能定义为可判断出单的标准预算。
- 新品 Auto / Broad / Phrase 可执行高流量核心词精准否定隔离，但必须使用当前类目已维护的隔离阈值。Rug 当前阈值为 `推荐层级=P1/P2` 且 `ABA排名<=11000`；其他类目未维护阈值时，不得套用 Rug 阈值，只能输出待配置。
- 用户问 Rug 类目新品广告需要输入哪些信息时，必须按 Rug 输入模板字段回答，不要把系统侧 ABA 表字段、功能、场景、人群/宠物、是否冷启动等泛化字段列为用户默认必填。
- Rug 产品如果有具体动物图案，必须使用 `图案动物类型` 做强匹配；该字段可由用户手动填写，也可由图片识别得到。动物类型不明确时不得推荐具体动物 ABA 关键词。
- 新品推广一般没有稳定 CPA / CVR / ACOS 阈值参考；可以用类目 CPA 正常线上限计算标准最低日预算，但不能用短期 CPA / CVR / ACOS 直接强判暂停、否词或放量。
- 新品阶段不能用短期 CPA / CVR / ACOS 直接强判暂停、否词或放量；如果当前链接已有稳定广告数据，应转入老品推广。
- 老品推广必须同时考虑：老广告如何优化、新广告是否需要新增/并入/重建。
- 老品出单词达到当前类目优质线且表现稳定时，可以做跨广告产品拓量；必须先保留原 SP，再按素材和资质新增 SPV / SB / SBV 等复制验证。该动作只能来自当前链接真实报表，不能用类目历史出单词直接放量。
- 老品推广输入报表名称必须按 `agents/old-product-promotion.md` 的“老品输入报表命名标准”输出，不要使用泛化报表名替代。
- 搜索词投放优先从历史出单搜索词和词根表现出发，ABA 主要用于判断市场容量、稳定流量和长期排名机会。
- ABA 类目流量结构判断只回答入口数量、头部集中度和打法方向，不等于具体产品选词；产品级承接必须结合产品属性、阶段和历史出单证据。
- 当前链接自己的搜索词数据优先级最高；类目历史出单词数据只作为同类历史参考，不能覆盖当前链接真实表现。
- 类目历史出单词数据不得作为老品方案的数据源报表；只能作为“选词参考 / 新增词候选 / 可复用词池”使用。
