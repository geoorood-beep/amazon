# UTA-amazon-ads 版本

系统名称：`UTA-amazon-ads`（2026-11-17 起统一使用；此前 README / AGENTS.md / 本文件分别叫“亚马逊广告智能体”“Amazon 广告 AGENTS 集合”“lulu 广告智能体”，均指本系统）。

`lulu` 只是广告组命名中的**运营名**（`SPU-广告产品-定向维度-匹配方式-场景分类-尺寸-运营名`），不是系统名称。

当前版本：`V1.3`

版本日期：`2026-11-17`

## V1.3 新增范围

- **三层架构**：通用规则 `agents/` ＋ 通用知识 `knowledge/ads-framework/` ＋ 品类层 `categories/<品类>/`。换品类只加品类目录，不改通用层。
- **品类注册表** `categories/README.md`：状态分已开通 / 知识中 / 待建；`_template/` 复制即开通新品类。喂水器 `pet_water_fountain` 已开通；喂食器 `pet_feeder`、智能猫厕所 `smart_litter_box` 占位。
- 喂水器迁到品类目录：品类卡 `category.md`、阈值 `thresholds.md`（从 `agents/category data thresholds.md` 拆出，唯一权威来源）、引擎配置 `engine.json`、运营数据仓 `ops/`。
- **课程知识分解**：总纲 V2.0、两份 Soju 导图和负责人口径改写为通用方法论——【标准】49 条、【建议】14 条、【待补】30 条，每条写明触发、动作、出处章节、引擎落地状态。课程原文不进本公开仓库。
- **宠物用品知识库并入**：负责人口径原件进 `knowledge/ads-framework/decisions/`；狗猫准词表、投放词池、历史出单词、初版架构、首推词表、西柚周扫描进 `categories/pet_water_fountain/knowledge/`。私有原仓库 `geoorood-beep/pet-supplies-amazon-ads` 归档（保留课程原文）。
- 引擎按 `--category` 读取 `categories/<品类>/engine.json`；未开通品类或无阈值时明确报错。
- `GROK.md` 增加“定品类”一步，复述检查改为 6 项；Grok 不再需要登录私有仓库。

## V1.2 新增范围

- 系统名称统一为 `UTA-amazon-ads`。
- Grok 云端电脑操作员 SOP：`agents/grok-operator.md`。领星无开放接口，由 Grok 网页操作领星，每周导出报表、补齐档案，并照已审批的执行指令单执行，含核对当前值、单次 30 行、二次确认等护栏。
- 运营数据仓：`categories/pet_water_fountain/ops/`，通过 GitHub 累积报表、产品档案、缺失项、领星操作路径、交接记录、执行日志和改动历史；数据成熟度 L0-L4 决定可输出的动作。
- 喂水器老品规则引擎：`old_product_module/`，按 10L / 5L 阈值确定性计算搜索词否定、竞价、广告位溢价、预算、出单词加词，输出方案报告和执行指令单草稿。
- 目标 CPA 与竞价单次调整上限按历史数据自动推导，不再要求人工设定。
- 自有品牌词 `meandu`、`pokpet`：含品牌词的搜索词不否定。
- 接入宠物用品广告知识库 `geoorood-beep/pet-supplies-amazon-ads`（用户确认「确定搭建」）：`agents/knowledge-base.md` 定义判断优先级、6 处冲突裁决和 Grok 每周综合判断流程；引擎新增竞品品牌词保护、零转化按匹配方式对比、竞价层级检查，广告位动作改为人工复核。

## V1.1 固定范围（2026-07-07）

- 广告组统一命名：`SPU-广告产品-定向维度-匹配方式-场景分类-尺寸-运营名`。
- 单关键词广告组名称支持 ABA 大致排名标记，例如 `runner rug(4k)`、`area rug(1.8w)`。
- 新广告标准最低日预算按类目 CPA 正常线上限计算，不按 CPC 推算。
- Rug 新品输入字段按 `新品基础信息输入模版_Rug类目` 收敛。
- Rug ABA 关键词库替换为 `reference/rug-aba/` 下 4 个场景文件，调用时只读取每个文件的 `广告词库` sheet。
- Rug 动物图案关键词按 `图案动物类型` 强匹配。
- Rug 历史出单词库固定到 `reference/category-history/rug/`。
- Rug 新品 Auto / Broad / Phrase 支持高流量核心隔离否词：`推荐层级=P1/P2 + ABA排名<=11000`，默认 `Negative Exact`。
- 老品优质出单词支持跨广告产品拓量：SP 表现稳定后，可复制验证 SPV / SB / SBV。
