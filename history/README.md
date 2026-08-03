# 历史规则与文档

本目录只用于追溯，不参与当前任务读取和规则解析。

## 当前快照

`v1.4-pre-8layer/` 保存八层拆分前的 `AGENTS.md` 和全部子 AGENT 原文。拆分后的旧路径已经改为兼容入口；需要核对是否漏掉历史细节时，在这里对照。

## 状态规则

- `history/` 中任何数值和规则均为 `HISTORICAL_ONLY`；
- 不得从历史文件直接生成广告动作；
- 需要恢复旧文件时先核对 manifest SHA-256；
- 历史内容要重新启用，必须迁移到 `rules/` 或 `thresholds/`，记录来源并通过校验；
- `docs/v2/source/` 保存 V2 架构和漏洞来源，仍是来源材料，不是当前机器 ACTIVE 规则包。

文件校验见 `v1.4-pre-8layer/MANIFEST.md`；旧章节的当前落点见 `v1.4-pre-8layer/MIGRATION_MAP.md`。
