# 亚马逊广告智能体

本仓库用于管理 Amazon 广告智能体的 AGENTS 规则、固定参考数据、类目历史选词数据和新品推广辅助模块。

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

- `agents/new-product-promotion.md`：新品推广选词与广告架构搭建。
- `agents/old-product-promotion.md`：老品推广优化主流程。
- `agents/search-term-reinvestment.md`：搜索词再投放、词根聚合、ABA 匹配。
- `agents/category-history-data.md`：类目历史出单词数据管理，只做选词参考。
- `agents/category data thresholds.md`：品类阈值标准。
- `agents/promo-output-templates.md`：输出表格模板。

## 固定参考数据

- `reference/ABA喂水器.xlsx`
- `reference/通用地毯类目ABA关键词库_202605_v2.xlsx`
- `reference/category-history/pet_water_fountain/`

注意：类目历史出单词数据只用于选词参考、新品选词和新广告候选词，不是老品推广方案的数据源报表。

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

## 本地验证

```bash
cd new_product_module
python3 -m unittest discover -s tests -v
```
