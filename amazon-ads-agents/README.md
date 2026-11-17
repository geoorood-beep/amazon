# UTA-amazon-ads V1.5

`UTA-amazon-ads` 是本仓库的亚马逊广告智能体系统，用于管理 AGENTS 规则、固定参考数据、类目历史选词数据、运营数据仓和新品 / 老品推广模块。系统名称统一为 `UTA-amazon-ads`；`lulu` 只是广告组命名里的运营名。

当前版本：`V1.5`（版本说明见 `VERSION.md`）

V1.5 重点升级：行业基准与自有历史——每周累积卖家后台 SQP 和自有搜索词报表，方案报告对比市场 CTR / CVR、推算 CPA，并给出阈值复核建议（只建议，审批后才改阈值）。

V1.4 重点升级：Grok 自动读取 `main` 最新规则（`GROK.md` 第 0 步版本核对与更新提示），自定义指令设置一次即可；各版本写“Grok 须知”；版本号一致性测试。

V1.3 重点升级：多品类架构 `categories/`（喂水器已开通，喂食器、智能猫厕所占位）；课程知识分解为通用方法论 `knowledge/ads-framework/`（标准 49 条、建议 14 条、待补 30 条）；宠物用品知识库并入；引擎按 `--category` 读取品类配置。

V1.2 重点升级：系统名称统一、Grok 云端电脑操作员 SOP、喂水器 GitHub 运营数据仓（`categories/pet_water_fountain/ops/`）、喂水器老品规则引擎（`old_product_module/`）、目标 CPA 与竞价上限按历史数据自动推导、品牌词 meandu / pokpet 保护。

V1.1 重点升级：广告命名和 CPA 预算统一、Rug 输入字段收敛、动物图案关键词强匹配、Rug 历史出单词库入库、高流量核心否词隔离、老品优质出单词跨 SPV / SB / SBV 拓量。

## 让 Grok 使用

把 `GROK.md` 末尾那段“自定义指令”放进 Grok 的自定义指令。之后对 Grok 说“分析一下喂水器广告”“导出本周报表”“执行本周指令单”，它会先读 `GROK.md`，按步骤走。

## 核心结构

```text
GROK.md               Grok 唯一入口
AGENTS.md
agents/
reference/
knowledge/ads-framework/  通用广告方法论（标准 / 建议 / 待补 / 负责人口径）
categories/           品类层：注册表、模板、每个品类的阈值 / 知识 / 运营数据仓 / 引擎配置
new_product_module/
old_product_module/   老品规则引擎（多品类，--category）
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
- `agents/grok-operator.md`：Grok 云端电脑取数、补数、照执行指令单在领星操作。
- `agents/knowledge-base.md`：三层知识的优先级、冲突裁决和每周综合判断流程。

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
