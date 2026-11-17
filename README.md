# 亚马逊资料归类仓库

本仓库把原先分散的 4 个亚马逊相关仓库归类到一起。每个子目录对应一个原仓库，并保留完整提交历史。

本仓库为**公开**仓库（用户确认 2026-11-17）。

## 子目录

| 子目录 | 原仓库 | 状态 | 用途 |
|---|---|---|---|
| `amazon-ads-agents` | [geoorood-beep/amazon-ads-agents](https://github.com/geoorood-beep/amazon-ads-agents) | **原仓库已归档（2026-11-17）**，以本目录为准，继续在这里开发 | UTA-amazon-ads 广告智能体（V1.3）：Grok 入口 `GROK.md`、通用规则、通用广告方法论、多品类目录（喂水器已开通）、老品规则引擎 |
| `luyao-ads-agent-v2` | [geoorood-beep/luyao-ads-agent-v2](https://github.com/geoorood-beep/luyao-ads-agent-v2) | **原仓库已归档（2026-11-17）**，以本目录为准 | 陆遥广告智能体：地毯类目专用的 Amazon 广告 AGENTS 项目（运行时 V2.1） |
| `Listing` | [geoorood-beep/Listing](https://github.com/geoorood-beep/Listing) | 原仓库保留 | Amazon、Walmart 与 Wayfair 的 Listing AGENTS 规则，用于按平台、类目、关键词库和风险库生成合规 Listing |
| `amz-sales-forecast` | [geoorood-beep/amz-sales-forecast](https://github.com/geoorood-beep/amz-sales-forecast) | 原仓库保留 | 亚马逊销量预测智能体说明（由本地「amz预测2.0」转换而来） |

已归档的原仓库只读，内容和历史都保留，需要时可在 GitHub 仓库设置里取消归档。

## 相关仓库

| 仓库 | 说明 |
|---|---|
| [geoorood-beep/pet-supplies-amazon-ads](https://github.com/geoorood-beep/pet-supplies-amazon-ads)（公开，**已归档 2026-11-17**，用户确认保持公开） | 宠物用品广告知识库，**已并入** `amazon-ads-agents/`：口径与方法论在 `knowledge/ads-framework/`（课程知识已改写为标准 / 建议 / 待补规则），狗猫喂水器词表与西柚周扫描在 `categories/pet_water_fountain/knowledge/`。原仓库只保留课程原文 `source/` 备查 |

## 广告智能体入口

- Grok：[`amazon-ads-agents/GROK.md`](amazon-ads-agents/GROK.md)
- 其他 AI：[`amazon-ads-agents/AGENTS.md`](amazon-ads-agents/AGENTS.md)
