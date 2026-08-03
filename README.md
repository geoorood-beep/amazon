# 陆遥广告智能体

地毯类目专用 Amazon 广告 AGENTS 项目。

- 项目路径：`/Users/leo/Documents/陆遥广告智能体`
- 当前规则版本：`V2.0`
- 冻结状态：`V2.0_FROZEN`
- 唯一允许类目：Rug / 地毯（`rug`）
- 项目边界配置：[config/project_scope.json](config/project_scope.json)
- 冻结发布：[releases/v2.0/RELEASE.md](releases/v2.0/RELEASE.md)
- GitHub私有仓库：[geoorood-beep/luyao-ads-agent-v2](https://github.com/geoorood-beep/luyao-ads-agent-v2)

## 固定数据映射

| 数据 | 路径 | 用途 |
|---|---|---|
| Rug ABA | [Area](reference/rug-aba/area_rug_ABA关键词库_202605_v8.xlsx)、[Bathroom](reference/rug-aba/bathroom_rugs_ABA关键词库_202605.xlsx)、[Kitchen](reference/rug-aba/kitchen_rugs_ABA关键词库_202605_v2.xlsx)、[Outdoor](reference/rug-aba/outdoor_rug_ABA关键词库_202605_v2.xlsx) | 新品选词、ABA 入口和产品属性校验 |
| Rug 历史出单词 | [标准化历史效果词 Excel](reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx) | 同类历史参考和新增词候选 |
| Rug 阈值确认原件 | [20260731 人工阈值回填原件](reference/category-threshold/confirmed/20260731_V1.4_人工阈值回填原件.xlsx) | V1.4 原件，作为 V2.0 阈值审计来源 |
| Rug 新品模块 | [new_product_module/](new_product_module/README.md) | 尺寸类型识别、属性冲突过滤和架构辅助 |

本项目不含宠物喂水器或办公椅固定数据。收到这些类目任务时，应切换到 `/Users/leo/Documents/有它广告智能体`。

## 八层架构与单一真源

| 人工要修改的内容 | 唯一入口 | 不应修改的地方 |
|---|---|---|
| 八层职责与路由 | [architecture/](architecture/README.md) | 领域规则文件 |
| 判断顺序、权限和动作关系 | [rules/](rules/README.md) | `agents/` 和 `history/` |
| 数值、区间、单位和确认状态 | [thresholds/](thresholds/README.md) | `rules/` |
| 输入输出字段与状态 | [contracts/](contracts/README.md) | 阈值文件 |
| 数据源、证据粒度和优先级 | [knowledge/](knowledge/README.md) | 动作规则 |
| 迁移前全文与哈希 | [history/](history/README.md) | 当前规则解析 |

[AGENTS.md](AGENTS.md) 只保留最高边界和任务路由。`agents/*.md` 只是旧路径兼容入口，不再维护规则正文或数值。人工导航见 [AGENTS 可点击目录](agents/agents-directory.md)。

## 数据边界

历史词和 ABA 只用于选词、类目结构和新增词候选，不能替代当前链接真实广告报表。老品预算、Bid、广告位、暂停、否词和放量必须先通过 V2.0 数据质量门、对象映射、归因成熟度和 Validator。

## 每周报表导入

```bash
python3 scripts/weekly_amazon_report_ingest.py --config config/weekly_amazon_report_ingest.json
```

导入与分析输出分别保存在本项目的 `imports/amazon_ads_weekly/` 和 `outputs/weekly_amazon_ads/`。

## 本地校验

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/validate_project_scope.py
.venv/bin/python scripts/validate_phase1_decisions.py
.venv/bin/python scripts/validate_v20_rules.py
.venv/bin/python -m pytest new_product_module/tests ai_ads/tests -q
.venv/bin/python scripts/stress_test_v20.py
.venv/bin/python scripts/v20_release_manifest.py
```

当前规则已于 `2026-08-03` 正式定义为 `V2.0`，采用八层可维护结构。V1.4 拆分前原文已冻结在 [history/v1.4-pre-8layer/](history/v1.4-pre-8layer/MANIFEST.md)，仅作为来源与历史追溯，不参与当前规则读取。
