# 喂水器老品广告规则引擎

把 `agents/old-product-promotion.md`、`agents/search-term-reinvestment.md`、`agents/category data thresholds.md` 里能量化的规则写成确定性代码：**数字由代码算，大模型只做解释和补充判断**。只用 Python 标准库，不需要安装任何依赖。

## 运行

```bash
cd old_product_module
py cli.py --reports ../ops/pet_water_fountain/weekly/2026-W47/raw --profile profile.json
```

- `--reports`：Grok 从领星导出的报表目录（文件名按 `agents/grok-operator.md` 的标准命名）。
- `--profile`：产品档案，复制 `profile.example.json` 改。`model` 必须是 `10L` 或 `5L`。
- `--maturity`：不填时读 `ops/pet_water_fountain/README.md` 的 `当前成熟度`。
- 输出默认写到报表目录同级的 `plan/`：
  - `方案报告.md`：产品策略摘要、报表缺失影响、活动概览、可执行动作、判断依据与设计逻辑、被拦截动作、观察清单
  - `执行指令单草稿.md`：按 `ops/pet_water_fountain/templates/execution-order-template.md` 格式，审批后交 Grok 执行
  - `actions.csv`：全部动作明细

macOS / Linux 用 `python3` 代替 `py`。

## 规则（v1）

| 模块 | 规则 | 来源 |
|---|---|---|
| 搜索词否定 | 同一广告组内搜索词点击 ≥15 且 0 单，或花费达到花费<2单高风险线 → `Negative Exact`；ASIN 搜索词 → 否定商品；命中 `protected_terms` 只观察；精准投放词本身不否定 | search-term-reinvestment.md 否词 |
| 投放对象竞价 | 近 14 天订单 <2 且达到点击<2单/花费<2单线：高风险降满幅，警戒降半幅；订单 ≥2 按 CPA 分级：警戒/高风险下调，优质且 ≥3 单且近 3 天未转差才上调 | old-product-promotion.md Bid 诊断 + 品类阈值 |
| 竞价公式 | `建议竞价 = 目标 CPA × 近14天 CVR`，单次调整不超过 `bid_cap_pct`（默认 20%），最低 `bid_floor`；无用户目标 CPA 时用品类 CPA 正常线上限 | 待用户确认 |
| 广告位 | 活动整体 CPA 优质/正常时不分析；整体不达标时，花费占比 ≥30% 且 CPA 警戒/高风险的位置溢价减半/降到 0；优质且占比 <20% 的位置 +10pp | old-product-promotion.md 广告位诊断 |
| 预算 | 日均花费 ≥ 预算 90% 且 CPA 优质/正常 → +20%（需二次确认） | old-product-promotion.md 整体效果 |
| 出单词拓量 | 点击 ≥20、订单 ≥2、CPA ≤ 链接平均且未单独投放 → 新建词组组；点击 >20 且订单 ≥4 → 精准；竞价不超过实际 CPC×(1+上限)；预算 = CPA 正常线上限 | search-term-reinvestment.md + 统一命名 |
| 成熟度门控 | L2 只解锁否定、降竞价、降溢价、暂停；L3 起解锁提竞价、提溢价、加预算、加关键词 | ops/pet_water_fountain/README.md |

缺当前竞价、预算或溢价的动作不进入指令单，只在报告里列为“被拦截”。

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
