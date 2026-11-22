# UTA-amazon-ads 版本

系统名称：`UTA-amazon-ads`（2026-11-17 起统一使用；此前 README / AGENTS.md / 本文件分别叫“亚马逊广告智能体”“Amazon 广告 AGENTS 集合”“lulu 广告智能体”，均指本系统）。

`lulu` 只是广告组命名中的**运营名**（`SPU-广告产品-定向维度-匹配方式-场景分类-尺寸-运营名`），不是系统名称。

当前版本：`V1.6`

版本日期：`2026-11-22`

## V1.6 新增范围

### Grok 须知

- 美国站宠物类广告选词或新品方案，从必读知识页打开最新版 H10 准词表，选对应品类；引用时写明表格日期和工作表名。
- 只用于选词和打法参考。品类状态、广告执行权限、预算及阈值均不修改。

## V1.5 新增范围

### Grok 须知

- 任务 A 每周多导一份：卖家后台品牌分析「搜索查询表现」（品牌视图、周，每个品牌一份），文件名 `搜索查询表现_<品牌>_<年>-W<周数>.csv`，放进同一个 `raw/`；需要登录时停下等用户。
- 呈现方案时，加上方案报告末尾“对比行业与自有历史”一节，标【行业基准】【自有历史】。
- 这些行业数字只说明问题方向，不能据此加否词、暂停、调价，也不能改阈值；`categories/*/benchmarks/` 由引擎生成，不要手改。

### 内容

- **行业基准与自有历史**：新增 `engine/benchmarks.py`。从 SQP 算每个搜索词的市场 CTR、市场 CVR、我们品牌份额；从 `ops/weekly/` 累积的搜索词报表算本型号 CTR、CVR、CPC、CPA 周序列和关键词分布；推算市场 CPA = 自有 CPC ÷ 市场 CVR。
- 方案报告新增“对比行业与自有历史”：三列对比（市场 / 自有 / 现行阈值）、阈值复核建议、本周搜索词对比市场、未投放市场词起始竞价参考。
- 每次运行引擎刷新 `categories/<品类>/benchmarks/基准线_<型号>.md` 和 `latest_<型号>.json`，GitHub 历史即基准线历史。
- 新规则：R-DIAG-07（对比市场判断问题出在哪一环）、R-DIAG-08（基准只给方向和复核，不触发动作、不自动改阈值）；S-15（默认参数）。`agents/knowledge-base.md` 优先级新增第 6 级。
- 阈值调整流程：引擎出复核建议 → 负责人审批 → 改 `thresholds.md` + `engine.json` → 升版本。

## V1.4 新增范围

### Grok 须知

- 每次任务都从 `raw.githubusercontent.com/.../main/` 重新读最新文件，不用记忆里的旧规则；`GROK.md` 和 `VERSION.md` 版本不一致时加 `?v=时间` 重读。
- 版本和上次不同时，先读本节“Grok 须知”并告诉用户变化，再开始任务。
- 复述 6 项里的版本一行，写明读自 `VERSION.md`、本次是否有更新。

### 内容

- **自动跟随最新版**：`GROK.md` 新增第 0 步（读最新版、版本核对、更新提示）；Grok 自定义指令改为指向 `main` 分支原始文件，**以后规则更新不用再改自定义指令**。
- 每个版本在本文件写“Grok 须知”，Grok 遇到新版本先读这里。
- 维护规则：改动影响 Grok 时版本号加一，`GROK.md` / `VERSION.md` / `AGENTS.md` / `README.md` 版本号必须一致，由引擎测试 `test_version_consistency` 检查。

## V1.3 新增范围

### Grok 须知

- 先定品类（`categories/README.md`），复述检查改为 6 项。

- **三层架构**：通用规则 `agents/` ＋ 通用知识 `knowledge/ads-framework/` ＋ 品类层 `categories/<品类>/`。换品类只加品类目录，不改通用层。
- **品类注册表** `categories/README.md`：状态分已开通 / 知识中 / 待建；`_template/` 复制即开通新品类。喂水器 `pet_water_fountain` 已开通；喂食器 `pet_feeder`、智能猫厕所 `smart_litter_box` 占位。
- 喂水器迁到品类目录：品类卡 `category.md`、阈值 `thresholds.md`（从 `agents/category data thresholds.md` 拆出，唯一权威来源）、引擎配置 `engine.json`、运营数据仓 `ops/`。
- **课程知识分解**：总纲 V2.0、两份 Soju 导图和负责人口径改写为通用方法论——【标准】49 条、【建议】14 条、【待补】30 条，每条写明触发、动作、出处章节、引擎落地状态。课程原文不复制进本仓库，仍可在原仓库（公开、已归档）查阅。
- **宠物用品知识库并入**：负责人口径原件进 `knowledge/ads-framework/decisions/`；狗猫准词表、投放词池、历史出单词、初版架构、首推词表、西柚周扫描进 `categories/pet_water_fountain/knowledge/`。原仓库 `geoorood-beep/pet-supplies-amazon-ads` 归档并保持公开（用户确认 2026-11-17，保留课程原文）。
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
