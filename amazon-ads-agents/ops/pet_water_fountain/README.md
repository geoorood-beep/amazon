# 宠物喂水器 广告运营数据仓

当前成熟度：`L0`
更新日期：`2026-11-17`
更新人：`初始化`

本目录由 Grok 云端电脑按 `agents/grok-operator.md` 持续累积，分析方（Claude / Codex）按 `AGENTS.md` 的规则读取并出方案。历史版本靠 GitHub 提交记录保存，不要覆盖或删除旧周目录。

阈值来源：`agents/category data thresholds.md` 喂水器 10L / 5L 不锈钢。
历史出单词参考：`reference/category-history/pet_water_fountain/`（只做选词参考，不做老品诊断）。
ABA：`reference/ABA喂水器.xlsx`。

## 目录结构

```text
ops/pet_water_fountain/
├── README.md                 本文件：结构 + 数据成熟度
├── product-profile.md        产品档案（逐步补齐）
├── data-gaps.md              缺失项清单（Grok 维护；需用户确认的单独列出）
├── lingxing-ui-map.md        领星菜单路径和导出步骤（Grok 累积）
├── handoff.md                每周交接记录（Grok → 分析方）
├── templates/
│   ├── weekly-checklist.md        每周导出清单模板
│   └── execution-order-template.md 执行指令单模板
├── weekly/
│   └── <年>-W<周数>/
│       ├── raw/              领星导出的原始报表（不改内容）
│       ├── checklist.md      本周导出清单
│       └── plan/             分析方输出的本周方案（报告 + 执行指令单草稿）
└── execution/
    ├── change-history.csv    所有已执行改动 + 7/14 天效果回填
    ├── <YYYYMMDD>_执行指令单.md
    ├── <YYYYMMDD>_执行日志.md
    └── <YYYYMMDD>_screenshots/
```

## 数据成熟度

成熟度决定分析方 **能输出哪些动作**。达不到的动作只能写“数据不足，仅观察”，与 `AGENTS.md` 的“先判断数据充分度再给动作”一致。

| 等级 | 达标条件 | 解锁的动作 |
|---|---|---|
| `L0` 未开始 | 无报表 | 无；只输出补数清单 |
| `L1` 档案齐 | `product-profile.md` 的“必填”全部有值（含用户确认的目标 ACOS/CPA、日预算总额、竞价调整上限） | 广告架构诊断方向、命名规范化建议 |
| `L2` 一周完整 | 至少 1 周 6 类必须报表齐全，且 `Campaign / Ad Group 设置表` 含活动/广告组/投放对象名称和当前竞价预算 | 否词（Negative Exact）、高花费无单降竞价、广告位溢价下调 |
| `L3` 连续 4 周 | 连续 4 周报表齐全（可看 3/7/14/30 天趋势） | 提高竞价、加预算、出单词迁移与放量、新建广告组、跨 SPV/SB/SBV 拓量判断 |
| `L4` 有反馈 | `change-history.csv` 至少 30 条改动有 14 天效果回填 | 校准竞价公式和单次调整上限、按历史改动效果调整规则 |

任一周报表缺失时，成熟度不降级，但该周方案只能使用实际导出的报表，缺失部分按 `agents/old-product-promotion.md` 的“缺失影响”说明。
