# 每周 Amazon 广告报表自动导入

当前项目：`陆遥广告智能体`，只允许分析 Rug / 地毯。导入报表中的对象不能可靠映射到 Rug 时，按 `DQ_BLOCKED` 处理，不得跨项目取数。

目标：每周从邮箱下载 Amazon 广告报表附件，按本项目老品推广标准报表归档，生成 `manifest.json` 和 `analysis_prompt.md`，再交给 Codex 按 AGENTS 规则分析。

## 不能直接做的事

不要把 Amazon、邮箱或 Seller Central 密码写进项目文件。脚本只从环境变量读取邮箱 IMAP 登录信息。

如果邮件里只有需要网页登录的下载链接，脚本会把它视为缺少附件；这种情况不能靠硬填密码稳定解决，应该改成 Amazon 后台定时报表附件、邮箱 IMAP、或 Amazon Ads API。

## 第一次配置

在本机 shell 配置以下环境变量：

```bash
export AMAZON_REPORT_IMAP_HOST="imap.example.com"
export AMAZON_REPORT_MAIL_USER="your-report-mailbox@example.com"
export AMAZON_REPORT_MAIL_APP_PASSWORD="your-mailbox-app-password"
```

如果是 Gmail、Outlook、企业邮箱，优先使用应用专用密码或 OAuth 授权，不要使用主密码。

## 本地检查

```bash
# 在解压后的项目根目录运行
python3 scripts/weekly_amazon_report_ingest.py --dry-run
```

没有配置邮箱环境变量时，可以先验证脚本：

```bash
python3 scripts/weekly_amazon_report_ingest.py --dry-run --allow-missing-env
```

## 手动文件夹导入

如果先手动下载了报表，把文件放进一个文件夹，然后运行：

```bash
python3 scripts/weekly_amazon_report_ingest.py --source-dir "/path/to/report-folder"
```

脚本会生成：

- `imports/amazon_ads_weekly/<run_id>/raw/`
- `imports/amazon_ads_weekly/<run_id>/extracted/`
- `imports/amazon_ads_weekly/<run_id>/classified/`
- `imports/amazon_ads_weekly/<run_id>/manifest.json`
- `imports/amazon_ads_weekly/<run_id>/analysis_prompt.md`

## 归档后本地聚合

六类报表识别完成后，不再把六张表逐张交给模型重算。准备一个本批次上下文 JSON（模板见 `config/ad_report_context.example.json`），然后运行：

```bash
.venv/bin/python scripts/build_ad_decision_packet.py \
  --source-dir "imports/amazon_ads_weekly/<run_id>/classified" \
  --context "/绝对路径/context.json" \
  --output-dir "outputs/weekly_amazon_ads/<run_id>"
```

智能体优先读取输出的 `ad_decision_packet.json`；人工可打开同目录 `ad_decision_packet.xlsx`。如果 Data Quality 不是 `DQ_PASS`，先修复报表、字段或映射，不进入广告判断。

## 老品必须识别的 6 类报表

1. `SP搜索词-按词-每日明细`
2. `SP搜索词-按词-汇总`
3. `SP投放对象 / 关键词 / 商品投放报告`
4. `SP广告位报告`
5. `SP广告商品报告`
6. `Campaign / Ad Group 设置表`

脚本的分类主要基于文件名。文件名不标准时会进入未分类清单，需要人工确认，不能自动当作某一类报表。

## 每周分析边界

分析必须先读：

1. `AGENTS.md`
2. `rules/domains/old-product/README.md`
3. `rules/domains/search-term/README.md`
4. `thresholds/README.md`
5. `rules/output/output-rules.md`
6. `contracts/data-input.md`

必须报表缺失时，先判断是否已识别出当前链接的 `SP搜索词-按词-汇总`或 `SP搜索词-按词-每日明细`：

- 如果连当前链接搜索词也没有，只输出缺失影响，不编造暂停、降 Bid、放量、否词或重建动作。
- 如果只有当前链接的历史搜索词，允许按 `rules/domains/old-product/input-and-modes.md` 的有限数据模式输出词根层评分和候选方案；缺失模块必须写 `【缺失数据】数据不足，无法准确判断`。不得写具体 Campaign / 广告组、Bid、广告位调整、否词实施、暂停、重建或跨广告产品放量。
