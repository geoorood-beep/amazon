# 亚马逊广告智能体 V1.1

本仓库用于管理 Amazon 广告智能体的 AGENTS 规则、固定参考数据、类目历史选词数据和新品推广辅助模块。

当前版本：`V1.1`

V1.1 重点升级：广告命名和 CPA 预算统一、Rug 输入字段收敛、动物图案关键词强匹配、Rug 历史出单词库入库、高流量核心否词隔离、老品优质出单词跨 SPV / SB / SBV 拓量。

## 核心结构

```text
AGENTS.md
agents/
reference/
new_product_module/
aba_stage_aggregation/
scripts/
```

## 子 AGENTS

- `agents/agents-directory.md`：AGENTS 目录与标准输入清单；用户输入 `AGENTS 目录` 时展示。
- `agents/new-product-promotion.md`：新品推广选词与广告架构搭建。
- `agents/old-product-promotion.md`：老品推广优化主流程。
- `agents/search-term-reinvestment.md`：搜索词再投放、词根聚合、ABA 匹配。
- `agents/category-traffic-strategy.md`：通过 ABA 判断类目流量入口结构和适合打法。
- `agents/category-history-data.md`：类目历史出单词数据管理，只做选词参考。
- `agents/category data thresholds.md`：品类阈值标准。
- `agents/promo-output-templates.md`：输出表格模板。

## 固定参考数据

- `reference/ABA喂水器.xlsx`
- `reference/rug-aba/`
- `reference/category-history/pet_water_fountain/`
- `reference/category-history/rug/`
- `reference/category-traffic/office_chair/`

注意：类目历史出单词数据只用于选词参考、新品选词和新广告候选词，不是老品推广方案的数据源报表。

注意：类目流量结构数据只用于判断 ABA 流量入口、竞对共用词和类目打法，不是老品当前广告诊断报表。

## 半自动同步到 GitHub

第一次使用前需要安装并登录 GitHub CLI：

```bash
brew install gh
gh auth login
```

之后在项目根目录运行：

```bash
./scripts/sync_to_github.sh
```

脚本会：

1. 检查 GitHub CLI 和登录状态。
2. 自动创建私有仓库 `amazon-ads-agents`，如果仓库已存在则复用。
3. 自动提交本地变更。
4. 推送到 GitHub `main` 分支。

可以传入提交说明：

```bash
./scripts/sync_to_github.sh "更新老品输入表命名标准"
```

## 每周 Amazon 报表自动导入

自动导入入口：

```bash
python3 scripts/weekly_amazon_report_ingest.py --dry-run
```

说明见：

```text
docs/weekly-amazon-report-automation.md
```

## 本地验证

```bash
cd new_product_module
python3 -m unittest discover -s tests -v
```
