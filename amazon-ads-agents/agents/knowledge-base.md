# AGENT: 知识融合规则（通用规则 + 通用知识 + 品类层）

UTA-amazon-ads 的判断来自三层，本文件规定**谁优先、冲突怎么裁、每周怎么综合判断**。

| 层 | 位置 | 回答什么 |
|---|---|---|
| 通用规则 | `agents/` | 老品诊断、新品架构、搜索词复投、输出模板、Grok 操作（UTA 自己的 SOP） |
| 通用知识 | `knowledge/ads-framework/` | 跨品类的广告方法论：【标准】`standards/`、【建议】`suggestions.md`、【待补】`pending.md`、负责人口径原件 `decisions/` |
| 品类层 | `categories/<品类>/` | 品类卡、阈值、引擎配置、品类知识（准词表、架构、西柚周扫描）、运营数据仓 |

来源说明：通用知识由原仓库 `geoorood-beep/pet-supplies-amazon-ads`（公开，已归档） 的总纲、导图和负责人口径**分解改写**而成（2026-11-17 用户确认「确定搭建」并合并）。课程原文留在该原仓库 `source/`，本仓库只有改写后的规则和出处章节号；该原仓库已归档并保持公开（用户确认 2026-11-17）。

## 一、判断优先级（从高到低）

| 级别 | 来源 | 用途 |
|---|---|---|
| 1 | 当前链接真实报表 `categories/<品类>/ops/weekly/` | 所有老品诊断动作的唯一数据源 |
| 2 | 负责人口径：`knowledge/ads-framework/decisions/`；品类卡 `categories/<品类>/category.md` 的负责人口径；用户固定规则（品牌词、自动目标 CPA、1 倍预算等） | 口径冲突时以此为准 |
| 3 | 品类阈值 `categories/<品类>/thresholds.md` | CPA / CVR / ACOS 分级、停止线、标准预算 |
| 4 | 通用【标准】`knowledge/ads-framework/standards/` 与 `agents/` 规则 | 打法逻辑、竞价层级、放量缩量、诊断顺序 |
| 5 | 通用【建议】`knowledge/ads-framework/suggestions.md` | 变量规则，进方案需审批 |
| 6 | 行业基准与自有历史 `categories/<品类>/benchmarks/`（V1.5，引擎每周刷新） | 判断问题方向（转化 / 点击率低于市场）、新词起始竞价参考、阈值复核建议（R-DIAG-07、R-DIAG-08） |
| 7 | 品类知识 `categories/<品类>/knowledge/`、`reference/` | 只用于选词、加词候选、相关性参考 |

级别 6、7 不得作为否词、降价、暂停、提价、加预算的依据，只能补充候选词、给出诊断方向或降低动作强度（例如把否词降级为观察）。

### 美国站宠物类目准词参考

做美国站宠物类广告选词、新品方案或流量打法判断时，先从[宠物类目选词入口](../knowledge/ads-framework/README.md#美国站宠物类目选词入口)打开最新版 H10 准词表，只查对应品类工作表。若在方案中引用，注明【准词表】、表格日期和工作表名；如果表打不开，明确标注未核验，不用其他品类的词替代。

同一入口也须读取同品类的违禁词库，与 H10 候选一起复核。按适用位置和成立条件审查广告创意及相关商品页；Generic Keywords 禁项不得直接作为广告定向或否词规则；相关竞品品牌词可按适用的美国站广告类型及政策用于关键词定向，不放入 Sponsored Brands／Display 对客文案，不自动开投。引用时注明所用的版次和工作表；未读到则标未核验。

它只提供候选词和推广方向，不替代当前广告报表，不改变品类开通状态、阈值、预算或执行审批。

## 二、硬性边界（长期有效）

1. 【待补】`knowledge/ads-framework/pending.md` 的 30 条：补充确认前只能写“建议 / 人工复核”，**不进执行指令单**。
2. 【建议】里的数字是变量，不得写死成全类目常数；进方案必须标【建议】并由用户审批。
3. 以下 4 项任何时候都不能填一个数后自动执行：自动广告相对一级词的 `0.x`、VCPM 归因范围、广告位“基于规则”倍率、待补规则其余项。
4. 品类状态不是“已开通”时（见 `categories/README.md`），只按通用规则给建议，不出执行指令单。
5. 不同品类的阈值、品牌词、准词表、基准线不得互相借用。
6. 行业基准和自有历史**不自动改阈值**：引擎只出“阈值复核建议”，负责人审批后才同时改 `thresholds.md` 和 `engine.json`，并升版本（R-DIAG-08）。

## 三、冲突裁决（2026-11-17）

| # | 冲突 | 裁决 | 落地 |
|---|---|---|---|
| 1 | 新广告组预算：UTA 1 × CPA 正常线上限 vs 测试期 3–5 个目标 CPA | **用户确认保持 1 倍**；3–5 倍只在方案里列参考 | 品类 `engine.json` `new_group_budget_cpa_multiple = 1`；`suggestions.md` S-04 |
| 2 | 广告位调价门槛未定（待补 P-17、P-18） | 广告位动作一律人工复核，不进指令单 | `engine.json` `placement_manual_review = true`；`standards/广告位.md` |
| 3 | 投放词零转化 | 先比较同词各匹配方式出单，再决定停或降 | 引擎已实现；`standards/否词与缩量.md` R-NEG-05 |
| 4 | 竞价层级 | 精准 > 词组 > 广泛 > 自动，倒挂提价被拦截 | 引擎已实现；`standards/竞价.md` R-BID-01 |
| 5 | 竞品品牌词 | 不自动否定、不自动加词，列观察 | 品类 `engine.json` `competitor_brand_terms`；R-NEG-03 |
| 6 | 执行门槛 | 已确认「确定搭建」；待补 30 条按第二节处理 | 本文件 |

## 四、每周综合判断流程（Grok / 分析方）

1. **定品类**：在 `categories/README.md` 找到品类 key 和状态。
2. **取数**：`categories/<品类>/ops/weekly/<周>/raw/`（领星报表）＋ `categories/<品类>/knowledge/keyword-weekly/`（西柚周扫描，如有）＋ 品类准词表。
3. **算数**：`cd old_product_module && py cli.py --category <品类> --reports ../categories/<品类>/ops/weekly/<周>/raw --profile <档案>`。否词、竞价、预算、加词的**数字只认引擎结果**，不得自行改数。方案报告末尾的“对比行业与自有历史”一节同时给出市场 / 自有 / 现行阈值三列对比，只用于诊断方向和阈值复核。
4. **按通用标准逐条复核**（规则编号写进方案）：
   - 否词：是否自有 / 竞品品牌词、准词表高分词或西柚飙升词（R-NEG-02、R-NEG-03、R-NEG-04）→ 是则降级为观察。
   - 零转化投放词：复核词根频次（R-NEG-05）。
   - 加词：用准词表和西柚“可马上加入广告”的词补候选，标注放量方式 S1–S6（R-SCALE-02）。
   - 竞价：层级不倒挂（R-BID-01、R-BID-02、R-BID-06）。
   - 曝光低：按 R-DIAG-01 排查后才建议提价。
   - 诊断顺序按 R-DIAG-03 组织方案；活动目标按 R-GOAL-01 标定。
   - 广告位、瀑布流、AMC、待补规则相关：只写建议，交人工。
5. **呈现**：分析结果**先在聊天里用中文表格呈现**（`decisions/运营方法论_领星西柚.md` §1），用户点头后才写入 `categories/<品类>/ops/weekly/<周>/plan/` 和执行指令单。关键词保留英文。
6. **来源标签**：`【当前报表】【品类阈值】【用户固定规则】【行业基准】（SQP 市场数）【自有历史】（ops 累积周报）【知识库-口径】（decisions/）【知识库-标准】（standards/，写规则编号）【知识库-建议】（suggestions.md）【准词表/西柚】【缺失数据】`。
7. 用户审批后，Grok 按 `agents/grok-operator.md` 任务 B 执行。

## 五、按问题查文件

| 问题 | 文件 |
|---|---|
| 口径冲突以谁为准 | `knowledge/ads-framework/decisions/口径与决策记录.md` |
| 活动目标、决策关口、打法、架构模板 | `knowledge/ads-framework/standards/目标与架构.md` |
| 竞价层级、基准 x、有效竞价、基准竞价测试 | `knowledge/ads-framework/standards/竞价.md` |
| 否词、品牌词、竞品词、零转化、缩量 | `knowledge/ads-framework/standards/否词与缩量.md` |
| 放量方式、搜索词分层、拆组、瀑布流 | `knowledge/ads-framework/standards/放量.md` |
| 曝光低、CTR/CVR/CPA、账户诊断顺序、自然位 | `knowledge/ads-framework/standards/诊断.md` |
| 广告位 | `knowledge/ads-framework/standards/广告位.md` |
| 变量（倍率、测试预算、晋级门槛） | `knowledge/ads-framework/suggestions.md` |
| 还没定义的规则 | `knowledge/ads-framework/pending.md` |
| 领星报表呈现、竞品反查、西柚节奏 | `knowledge/ads-framework/decisions/运营方法论_领星西柚.md` |
| 某品类的阈值 / 品牌词 / 准词表 / 报表 | `categories/<品类>/` |
