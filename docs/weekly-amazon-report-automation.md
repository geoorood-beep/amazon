# 每周 Amazon 广告报表自动导入

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
cd "/Users/leo/Documents/广告智能体 2"
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
2. `agents/old-product-promotion.md`
3. `agents/search-term-reinvestment.md`
4. `agents/category data thresholds.md`
5. `agents/promo-output-templates.md`

必须报表缺失时，只输出缺失影响，不得编造暂停、降 Bid、放量、否词或重建动作。
