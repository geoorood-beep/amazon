---
name: amz预测2.0
description: Forecast Amazon sales and inventory decisions using parent-demand forecasting, child-ASIN/SKU share forecasting, anomaly correction, SKU-type-specific models, scenario ranges, replenishment planning, stockout and overstock warnings, and SKU-level backtesting. Use when analyzing Amazon sales, advertising, traffic, pricing, promotion, inventory, inbound, parent ASIN, child ASIN, SKU, replenishment, stockout, slow-moving inventory, 30/60/90-day demand, natural-month forecasts, 12-week forecasts, or forecast accuracy files and reports.
---

# amz预测2.0

## Core contract

Treat the forecast as an operational demand estimate, not a sales target.

Every forecast must output three scenario methods, with clear labels and no single-number-only result:

1. `保守估计(低估)` - downside / low-demand scenario.
2. `正常预估` - baseline expected scenario and the primary execution reference.
3. `乐观估计(高估)` - upside / high-demand scenario.

Apply the three methods at parent-ASIN, child-ASIN/SKU, 30/60/90-day, natural-month, and weekly forecast levels whenever those levels are produced.

Always use the two-layer structure:

1. Forecast total demand at parent-ASIN level.
2. Forecast child-ASIN/SKU shares and independent increments.
3. Convert SKU forecasts into inventory, replenishment, stockout, and slow-moving decisions.

Control both parent-level error and SKU-level error. Never accept a forecast only because the parent total is accurate.

For main-push SKUs (`主推款`), use a separate evidence-gated share model. Treat `主推款` as an operational intent, not a guaranteed sales outcome. Distinguish:

- `主推款`: the SKU the operator plans to push.
- `主力销量款`: the SKU currently winning the largest share from sales data.
- `潜力主推款`: a pushed SKU with rising share and enough operational support.
- `衰退主推款`: a pushed SKU whose share is falling or whose support has weakened.
- `无效/暂停主推款`: a pushed SKU with missing stock, weak ads, no price advantage, paused listing, or repeated high forecast error.

Never force the baseline forecast to make a main-push SKU the top-selling SKU by unconditional uplift. A main-push SKU can receive extra share only when there is evidence from recent share trend, inventory availability, advertising plan, price/coupon/deal support, traffic/CVR, Buy Box, review/rating, or explicit operational plan. If the user states "销量最多的是主推款", treat it as a hypothesis to test and an execution scenario to document, not as a hard mathematical override.

Read [references/forecast-rules.md](references/forecast-rules.md) before calculating or writing a final forecast. It is the authoritative source for classifications, formulas, warning thresholds, backtesting fields, output modules, and prohibited shortcuts.

## Workflow

### 1. Inspect and normalize inputs

- Identify date grain, marketplace, parent ASIN, child ASIN, SKU, currency, timezone, and units.
- Build the complete SKU pool from the union of sales, inventory, inbound, forecast, and active-listing data.
- Map every active SKU to a parent ASIN. Keep unmapped records in a visible exception table.
- Preserve source values. Create separate corrected-demand fields instead of overwriting actual sales.
- Use structured spreadsheet parsing for XLSX/CSV inputs.

Create a data-availability matrix for:

- Sales history: 7/14/28/56/90 days and prior-year comparable periods
- Parent-child mapping
- Sellable, inbound, receiving, and reserved inventory
- Stockout and low-inventory dates
- Sessions, CVR, advertising clicks, CPC, budget, and attributed orders
- Price, coupon, deal, event, Buy Box, BSR, review, and rating history
- Main-push evidence: main-push flag source/date, planned ad budget, planned coupon/deal, planned price, inventory coverage, listing active status, and whether the main-push tag is still valid
- Lead time, safety-stock policy, and operational intervention plans

Do not invent missing fields. State which model components are unavailable and lower confidence accordingly.

### 2. Correct suppressed and abnormal demand

- Mark stockout, low-stock suppression, Buy Box loss, budget exhaustion, listing restriction, delayed receiving, event, coupon, price, advertising, and listing-change dates.
- Exclude abnormal dates from ordinary baselines when appropriate.
- Estimate lost demand for constrained dates using the rule reference.
- Keep actual sales, estimated lost sales, and corrected demand as separate columns.

### 3. Forecast parent demand

- Use a model combination, not a simple average.
- Compare short-, medium-, and long-window baselines.
- Add trend, seasonality, prior-year, traffic, conversion, advertising, price, promotion, ranking, review, and operational adjustments when data exists.
- Produce `保守估计(低估)`, `正常预估`, and `乐观估计(高估)` scenarios. Do not provide only one forecast value.
- Produce 30-, 60-, and 90-day forecasts, three natural-month forecasts, and 12 weekly forecasts.
- Record assumptions and confidence drivers.

### 4. Forecast child shares and SKU demand

- Calculate 7/14/28/90-day and prior-month shares within each parent.
- Detect continuously rising or falling shares, new-product ramp, old-product decline, cannibalization, passive share gains caused by sibling stockouts, and advertising-driven shifts.
- Classify each SKU before selecting a model: mature active, new/ramping, low-active/long-tail, or forecast-coverage missing.
- Classify main-push status before applying any main-push adjustment: `主推款`, `主力销量款`, `潜力主推款`, `衰退主推款`, or `无效/暂停主推款`.
- Use dynamic main-push weights bounded by evidence. Apply share caps and rolling backtest correction before normalizing shares.
- If the current top-selling SKU is not a main-push SKU, do not force the normal forecast to change rank. Instead output the demand gap, required operational support, and whether the top-rank scenario is plausible.
- Calculate:

```text
SKU forecast = parent forecast × predicted SKU share + independent SKU increment
```

- Normalize predicted shares when necessary and explain any independent increment that causes SKU totals to differ from the parent baseline.
- Never default an eligible low-active SKU to zero.

### 5. Convert demand into inventory decisions

- Calculate forecast daily sales, safety stock, reorder point, inventory days, estimated stockout date, and suggested replenishment quantity.
- Use SKU-level demand for replenishment decisions, not only parent totals.
- Separate valid inbound inventory from inbound that will arrive too late.
- Apply the stockout and slow-moving warning thresholds from the rule reference.
- State timing, quantity, transport urgency, and operational actions.

### 6. Diagnose uncertainty and error

- Output confidence and error-risk level for every parent and SKU.
- Widen ranges for new, volatile, event-driven, seasonal, or data-poor SKUs.
- When actuals exist, calculate parent variance, SKU wMAPE, absolute error, Bias, high-error SKU counts, new/old product errors, and omitted long-tail sales.
- For main-push SKUs, calculate main-push share error, rank error, repeated high-bias direction, main-push evidence score, share cap hit, and rolling correction coefficient.
- Explicitly state: `父体预测可接受，但子体结构预测失败` when parent error is acceptable but SKU wMAPE is high.
- Recommend model-weight changes based on the error diagnosis.

### 7. Produce the required outputs

Default output must be compact. Do not create many separate worksheets unless the user explicitly asks for detailed appendices.

By default, export only two core worksheets:

1. `01_预测数据`: one forecast data table. It must combine parent-ASIN and child-ASIN/SKU forecast data in one sheet, including the three scenarios, parent total, SKU allocation, main-push status, share, confidence, and the key assumptions needed to understand the number.
2. `02_诊断校准`: one diagnosis and calibration table. It must combine monthly accuracy, overall accuracy, corresponding SKU-level reconciliation, error reason, and next calibration action in one sheet.

When actual sales are available for calibration, the workbook must use a hierarchy-friendly accuracy template:

- In `01_预测数据`, use one wide table with one row per parent and one row per child-ASIN/SKU. Place every child row directly under its parent row.
- Include filter-friendly identity columns before metrics: `组别`, `层级`, `父ASIN`, `父体名称`, `子ASIN`, `SKU`, `层级显示`, `主推标记`, `主推分类`, `SKU类型`, `是否预测覆盖缺失`, and `是否超过20%误差`.
- For each forecast month, keep the three forecast methods and actual values adjacent: `{月份}保守预测`, `{月份}正常预测`, `{月份}乐观预测`, `{月份}真实`, `{月份}正常差异`, `{月份}正常准确率`.
- Include the full-period calibration block in the same row: `3个月保守预测`, `3个月正常预测`, `3个月乐观预测`, `3个月真实`, `3个月正常差异`, `3个月MAPE`, `3个月正常准确率`, `3个月区间命中`, and, when applicable, `干预前预测`, `干预前准确率`, `干预后准确率提升`.
- Forecast quantity columns and forecast accuracy columns should be visually highlighted, and monthly metric blocks should use alternating light white/gray fills when exported to a spreadsheet.
- Parent rows should be visually distinct from child rows, but must stay in the same worksheet so filtering by `父ASIN`, `层级`, `主推标记`, coverage-missing status, or high-error status remains simple.
- In `02_诊断校准`, keep the row-level long-form audit, but still place `保守预测`, `正常预测`, `乐观预测`, `真实`, `差异`, `绝对误差`, `MAPE`, and `准确率` next to each other.

Optional detailed worksheets such as raw history, category trend, deal evidence, inventory warnings, stockout warnings, slow-moving warnings, or full share-change history should not be created by default. Include those details as compact fields inside the two core worksheets, or create appendices only when the user asks for them or when a blocking data exception cannot be understood without a separate appendix.

Lead with the two tables and a short conclusion. Keep calculations traceable, but do not spread the result across unnecessary tabs.

## Quality checks

Before finalizing, verify:

- Parent forecasts reconcile with SKU allocations or explain the difference.
- Predicted child shares are logically bounded and normally sum to 100%.
- Every forecast table includes `保守估计(低估)`, `正常预估`, and `乐观估计(高估)` for the relevant forecast horizon.
- No active, stocked, inbound, or recently selling SKU is silently omitted.
- Stockout days are not treated as ordinary zero-demand days.
- New products are not projected by naive 7-day linear scaling.
- Declining old products are not replenished from stale historical highs.
- Main-push SKUs are not inflated by a fixed multiplier or forced to rank first without evidence.
- Predicted main-push share does not exceed recent-share caps unless the report shows explicit inventory, ad, price, coupon, deal, or traffic evidence.
- Repeatedly overestimated or underestimated main-push SKUs use a rolling correction coefficient in the next forecast.
- Default workbook contains only `01_预测数据` and `02_诊断校准`, unless the user explicitly requested more sheets.
- Monthly accuracy, overall accuracy, and SKU-level reconciliation are all present in `02_诊断校准`.
- Forecast, target, and scenario assumptions are clearly separated.
- Every important number is traceable to a source field, formula, or explicit assumption.
