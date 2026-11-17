# 老品广告规则引擎（多品类通用）

把 `agents/old-product-promotion.md`、`agents/search-term-reinvestment.md` 和 `knowledge/ads-framework/standards/` 里能量化的规则写成确定性代码：**数字由代码算，大模型只做解释和补充判断**。只用 Python 标准库，不需要安装任何依赖。

一套代码服务所有品类：品类的阈值、品牌词、竞品词、预算倍数都在 `categories/<品类>/engine.json`，换品类只换配置。

## 运行

```bash
cd old_product_module
py cli.py --category pet_water_fountain --reports ../categories/pet_water_fountain/ops/weekly/2026-W47/raw --profile profile.json
```

- `--category`：品类 key（见 `categories/README.md`），默认 `pet_water_fountain`。品类没有 `engine.json` 或没配阈值时直接报错，不借用其他品类。
- `--reports`：Grok 从领星导出的报表目录（文件名按 `agents/grok-operator.md` 的标准命名）。
- `--profile`：产品档案，复制 `profile.example.json` 改。`model` 必须是该品类 `engine.json` 里 `models` 的一个（喂水器：`10L` / `5L`）。
- `--maturity`：不填时读 `categories/<品类>/ops/README.md` 的 `当前成熟度`。
- 输出默认写到报表目录同级的 `plan/`：
  - `方案报告.md`：产品策略摘要、报表缺失影响、活动概览、可执行动作、判断依据与设计逻辑、被拦截动作、观察清单
  - `执行指令单草稿.md`：按 `categories/<品类>/ops/templates/execution-order-template.md` 格式，审批后交 Grok 执行
  - `actions.csv`：全部动作明细
- 同时刷新 `categories/<品类>/benchmarks/基准线_<型号>.md` 和 `latest_<型号>.json`（行业基准与自有历史，V1.5）；`--no-benchmarks` 关闭，`--ops-dir` / `--benchmarks-out` 覆盖目录（测试用）。

macOS / Linux 用 `python3` 代替 `py`。

## 规则（v1）

| 模块 | 规则 | 来源 |
|---|---|---|
| 搜索词否定 | 同一广告组内搜索词点击 ≥15 且 0 单，或花费达到花费<2单高风险线 → `Negative Exact`；ASIN 搜索词 → 否定商品；含自有品牌词（配置里固定 `meandu`、`pokpet`，档案可追加 `brand_terms` / `protected_terms`）只观察；精准投放词本身不否定 | search-term-reinvestment.md 否词 |
| 投放对象竞价 | 近 14 天订单 <2 且达到点击<2单/花费<2单线：高风险降满幅，警戒降半幅；订单 ≥2 按 CPA 分级：警戒/高风险下调，优质且 ≥3 单且近 3 天未转差才上调 | old-product-promotion.md Bid 诊断 + 品类阈值 |
| 竞价公式 | `建议竞价 = 目标 CPA × 近14天 CVR`，单次调整不超过上限，最低 `bid_floor` | 用户确认 2026-11-17 |
| 目标 CPA（自动） | `target_cpa` 不填或 `"auto"`：取链接自身历史 CPA，限定在品类优质线 ~ 正常线上限之间（10L：$20~$25；5L：$24~$30）；历史不足 10 单时用正常线上限。填数字则人工固定 | 用户决定按历史数据调控 |
| 调整上限（自动） | `bid_cap_pct` 不填或 `"auto"`：当前默认 20%，不逐条二次确认；L4 起按 `change-history.csv` 校准（见下） | 用户决定按历史数据调控 |
| 竞品品牌词 | 配置 `competitor_brand_terms`（selene、doggy spout、fresh flow，档案可追加）：搜索词含竞品品牌词时不自动否定、不自动加词，列入观察 | 知识库 docs/07 |
| 零转化投放词 | 触发停止线时，先看同一关键词在精准 / 词组 / 广泛是否出单：别的匹配出单 → 暂停本匹配（需二次确认）；都不出单 → 降竞价；词根在搜索词里仍有出单 → 降价观察并注明 | 知识库 docs/09 §3 |
| 竞价层级 | 同一关键词保持 精准 > 词组 > 广泛；会造成倒挂的提价被拦截，已有倒挂写进报告 | 知识库 docs/05 |
| 广告位 | 活动整体 CPA 优质/正常时不分析；整体不达标时给方向（差位置减半/降 0，好位置 +10pp）。**全部只做人工复核，不进指令单**（`placement_manual_review`），其中 30% / 20% / 15 次点击是引擎默认参考值，不是已确认规则 | old-product-promotion.md + 知识库第十四章第 17、18 条待补充 |
| 预算 | 日均花费 ≥ 预算 90% 且 CPA 优质/正常 → +20%（需二次确认） | old-product-promotion.md 整体效果 |
| 出单词拓量 | 点击 ≥20、订单 ≥2、CPA ≤ 链接平均且未单独投放 → 新建词组组；点击 >20 且订单 ≥4 → 精准；竞价不超过实际 CPC×(1+上限)；预算 = CPA 正常线上限 × `new_group_budget_cpa_multiple`（默认 1），同时列出知识库测试期 3–5 个目标 CPA 的参考区间；标注放量方式 S2 / S3 | search-term-reinvestment.md + 知识库总纲 §10 |
| 成熟度门控 | L2 只解锁否定、降竞价、降溢价、暂停；L3 起解锁提竞价、提溢价、加预算、加关键词 | categories/pet_water_fountain/ops/README.md |

缺当前竞价、预算或溢价的动作不进入指令单，只在报告里列为“被拦截”。

## 行业基准与自有历史（V1.5，`engine/benchmarks.py`）

| 项 | 计算 | 用途 |
|---|---|---|
| 市场 CTR / CVR | SQP（`搜索查询表现_*.csv`）每个词的全市场 展示 → 点击 → 购买；市场点击 ≥50 才计入；自有品牌词不计入均值 | 诊断方向（R-DIAG-07） |
| 自有历史 | `ops/weekly/*/raw` 的 SP 搜索词汇总，按活动 / 广告组名中的型号过滤，滚动 12 周 | 周序列、关键词 CPA / CVR 分布 |
| 推算市场 CPA | 自有 CPC ÷ 市场 CVR | 参考 |
| 本周搜索词对比市场 | 我们点击 ≥20 的词：CVR 或 CTR < 市场 × 70% 标“低于市场”；CVR ≥ 市场 × 1.2 标“有放量基础” | 只给方向 |
| 未投放市场词起始竞价参考 | 目标 CPA × 市场 CVR；排除已投放、自有品牌词、竞品品牌词 | 新建广告参考 |
| 阈值复核建议 | 自有 ≥4 周且 ≥30 单时，有单词 CPA / CVR 中位数偏离现行阈值 15% 以上提示复核 | 负责人审批后才改阈值 |

参数在 `engine.json` 的 `benchmark`（【建议】S-15）。这一节**不产生任何执行动作**，也不写阈值文件（R-DIAG-08）。

## 调整上限校准（L4 起，分析方执行）

`change-history.csv` 有 ≥30 条改竞价记录回填了 14 天效果后，按下面的口径校准 `auto_bid_cap_default`（在 `categories/<品类>/engine.json`，按品类分别校准）：

- 降竞价后 14 天订单下降超过 50% 的占比 > 30%：降得太猛，上限下调到 15%，再不行到 10%。
- 降竞价后 14 天 CPA 没有改善（未下降）的占比 > 50%：降得不够，上限上调到 25%。
- 提竞价后 14 天 CPA 进入警戒线的占比 > 30%：提价太猛，提价单独用更低上限。
- 校准结果和依据写进 `categories/pet_water_fountain/ops/handoff.md`，改配置时提交说明写 `config(pet_water_fountain): 校准竞价上限`。

## 未实现（需分析方人工补充）

- 广告商品层（ASIN / 变体）诊断
- 小时花费节奏
- 跨 SPV / SB / SBV 拓量
- 搜索词语义相关性（不相关词直接否定）：交给大模型复核

## 列名适配

`engine/loaders.py` 的 `ALIASES` 同时支持亚马逊英文表头和常见领星中文表头。遇到识别不了的表头，报告会列出实际表头，把它加进 `ALIASES` 即可。

## 测试

```bash
cd old_product_module
py -m unittest discover -s tests -v
```

Windows 注意：仓库放在很深的目录时可能超过 260 字符路径限制导致读不到文件，请把仓库放在较短的路径下（如 `C:\work\amazon`）。
