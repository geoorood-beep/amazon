# Amz sales forecast

Amazon sales forecasting agent instructions converted from the local
`amz预测2.0` Codex skill.

This repository is instruction-first. Its purpose is to let another Codex or
agent environment use the same forecasting contract without depending on the
local skill installation.

## Repository Layout

- `AGENTS.md` - main agent instruction file for Codex-style agents.
- `references/forecast-rules.md` - authoritative detailed forecasting rules,
  formulas, output fields, warnings, and prohibited shortcuts.
- `skill/SKILL.md` - original local Codex skill entrypoint.
- `agents/openai.yaml` - original skill interface metadata.

## Forecast Contract

The agent must forecast Amazon demand with:

- parent-ASIN total demand forecasting
- child-ASIN / SKU share forecasting
- SKU-level replenishment, stockout, and slow-moving inventory decisions
- three scenarios: `保守估计(低估)`, `正常预估`, `乐观估计(高估)`
- default workbook output with only `01_预测数据` and `02_诊断校准`

`references/forecast-rules.md` is the source of truth when implementing or
reviewing forecast behavior.

## GitHub Note

The display name requested was `Amz sales forecast`. The repository slug uses
`amz-sales-forecast`, which is the GitHub-safe form without spaces.
