import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

const [payloadPath, outputPath, previewDir] = process.argv.slice(2);
if (!payloadPath || !outputPath) {
  throw new Error("Usage: name_keyed_workbook_builder.mjs <payload.json> <output.xlsx> [preview_dir]");
}

const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const workbook = Workbook.create();

const COLORS = {
  navy: "#17365D",
  blue: "#1F4E78",
  blueLight: "#D9EAF7",
  teal: "#0F6B78",
  green: "#2E7D32",
  greenLight: "#E7F4E8",
  amber: "#9A6700",
  amberLight: "#FFF4CE",
  red: "#B42318",
  redLight: "#FDE7E5",
  gray: "#5B6573",
  grayLight: "#EEF1F5",
  border: "#CAD3DE",
  text: "#17202A",
  white: "#FFFFFF",
};

const sheetNames = [
  "00_SUMMARY",
  "01_DEDUP_CHECK",
  "02_HIST_CAMPAIGN",
  "03_HIST_TARGET",
  "04_HIST_SEARCH_TERM",
  "05_HIST_PLACEMENT",
  "06_HIST_PRODUCT",
  "07_CURR_CAMPAIGN",
  "08_CURR_TARGET",
  "09_CURR_SEARCH_TERM",
  "10_CURR_PLACEMENT",
  "11_CURR_PRODUCT",
  "11B_CURR_STORE",
  "12_SETTINGS",
  "13_ISSUES",
  "14_EVIDENCE",
];
for (const name of sheetNames) workbook.worksheets.add(name);

const toNumber = (value) => {
  if (value === null || value === undefined || value === "") return 0;
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
};

const toDate = (value) => {
  if (!value) return null;
  return new Date(`${String(value).slice(0, 10)}T00:00:00Z`);
};

const columnName = (index) => {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
};

const titleBand = (sheet, title, subtitle, endColumn = "H") => {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${endColumn}1`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${endColumn}1`).format = {
    fill: COLORS.navy,
    font: { bold: true, color: COLORS.white, size: 16 },
    rowHeight: 30,
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${endColumn}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${endColumn}2`).format = {
    fill: COLORS.blueLight,
    font: { color: COLORS.navy, italic: true },
    rowHeight: 26,
    verticalAlignment: "center",
    wrapText: true,
  };
};

const addTable = ({ sheetName, title, subtitle, headers, rows, tableName, formats = {}, widths = {} }) => {
  const sheet = workbook.worksheets.getItem(sheetName);
  const endColumn = columnName(Math.max(headers.length - 1, 7));
  titleBand(sheet, title, subtitle, endColumn);
  sheet.getRangeByIndexes(2, 0, 1, headers.length).values = [headers];
  sheet.getRangeByIndexes(2, 0, 1, headers.length).format = {
    fill: COLORS.blue,
    font: { bold: true, color: COLORS.white },
    rowHeight: 28,
    wrapText: true,
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: COLORS.navy },
  };
  if (rows.length) {
    sheet.getRangeByIndexes(3, 0, rows.length, headers.length).values = rows;
    const table = sheet.tables.add(`A3:${columnName(headers.length - 1)}${rows.length + 3}`, true, tableName);
    table.style = "TableStyleMedium2";
    table.showFilterButton = true;
  } else {
    sheet.getRangeByIndexes(3, 0, 1, headers.length).values = [["无数据", ...Array(headers.length - 1).fill(null)]];
    sheet.getRangeByIndexes(3, 0, 1, headers.length).format = {
      fill: COLORS.amberLight,
      font: { color: COLORS.amber },
    };
  }
  const populatedRows = Math.max(rows.length, 1);
  for (const [indexText, format] of Object.entries(formats)) {
    sheet.getRangeByIndexes(3, Number(indexText), populatedRows, 1).format.numberFormat = format;
  }
  for (let index = 0; index < headers.length; index += 1) {
    const width = widths[index] ?? Math.min(Math.max(headers[index].length + 4, 12), 28);
    sheet.getRangeByIndexes(0, index, populatedRows + 3, 1).format.columnWidth = width;
  }
  sheet.getRangeByIndexes(3, 0, populatedRows, headers.length).format.verticalAlignment = "center";
  sheet.freezePanes.freezeRows(3);
  return sheet;
};

const metricHeaders = [
  "period_label",
  "object_type",
  "local_object_id",
  "campaign",
  "ad_group",
  "object_label",
  "window",
  "period_start",
  "period_end",
  "impressions",
  "clicks",
  "orders",
  "spend",
  "sales",
  "CTR",
  "CVR",
  "CPC",
  "CPA",
  "ACOS",
  "ROAS",
  "identity_quality",
];

const metricValues = (rows) => rows.map((row) => [
  row.period_label,
  row.object_type,
  row.local_object_id,
  row.campaign || "",
  row.ad_group || "",
  row.object_label || "",
  row.window,
  toDate(row.period_start),
  toDate(row.period_end),
  toNumber(row.impressions),
  toNumber(row.clicks),
  toNumber(row.orders),
  toNumber(row.spend),
  toNumber(row.sales),
  null,
  null,
  null,
  null,
  null,
  null,
  row.identity_quality,
]);

const addMetricSheet = ({ sheetName, title, subtitle, rows, tableName }) => {
  const values = metricValues(rows);
  const sheet = addTable({
    sheetName,
    title,
    subtitle,
    headers: metricHeaders,
    rows: values,
    tableName,
    formats: {
      7: "yyyy-mm-dd", 8: "yyyy-mm-dd", 9: "#,##0", 10: "#,##0", 11: "#,##0",
      12: "#,##0.00", 13: "#,##0.00", 14: "0.00%", 15: "0.00%", 16: "#,##0.00",
      17: "#,##0.00", 18: "0.00%", 19: "0.00x",
    },
    widths: { 0: 22, 1: 20, 2: 34, 3: 48, 4: 44, 5: 42, 6: 14, 7: 14, 8: 14, 20: 34 },
  });
  if (values.length) {
    const formulas = values.map((_, index) => {
      const row = index + 4;
      return [
        `=IF(J${row}=0,"",K${row}/J${row})`,
        `=IF(K${row}=0,"",L${row}/K${row})`,
        `=IF(K${row}=0,"",M${row}/K${row})`,
        `=IF(L${row}=0,"",M${row}/L${row})`,
        `=IF(N${row}=0,"",M${row}/N${row})`,
        `=IF(M${row}=0,"",N${row}/M${row})`,
      ];
    });
    sheet.getRangeByIndexes(3, 14, formulas.length, 6).formulas = formulas;
  }
  if (values.length) {
    sheet.getRangeByIndexes(3, 3, values.length, 3).format.wrapText = true;
    sheet.getRangeByIndexes(3, 0, values.length, metricHeaders.length).format.rowHeight = 32;
  }
  sheet.freezePanes.freezeColumns(6);
  return values.length;
};

const dedupHeaders = [
  "family", "check", "usage", "status",
  "provided_impressions", "canonical_impressions", "diff_impressions",
  "provided_clicks", "canonical_clicks", "diff_clicks",
  "provided_orders", "canonical_orders", "diff_orders",
  "provided_spend", "canonical_spend", "diff_spend",
  "provided_sales", "canonical_sales", "diff_sales",
];
const dedupRows = payload.window_checks.map((row) => [
  row.family, row.check, row.canonical_usage, row.status,
  toNumber(row.provided_impressions), toNumber(row.canonical_impressions), toNumber(row.difference_impressions),
  toNumber(row.provided_clicks), toNumber(row.canonical_clicks), toNumber(row.difference_clicks),
  toNumber(row.provided_orders), toNumber(row.canonical_orders), toNumber(row.difference_orders),
  toNumber(row.provided_spend), toNumber(row.canonical_spend), toNumber(row.difference_spend),
  toNumber(row.provided_sales), toNumber(row.canonical_sales), toNumber(row.difference_sales),
]);
const dedupSheet = addTable({
  sheetName: "01_DEDUP_CHECK",
  title: "01｜7/14/30天重叠窗口去重与一致性检查",
  subtitle: "只使用30天每日明细作为事实源；7天、14天和汇总表仅校验，绝不重复相加。",
  headers: dedupHeaders,
  rows: dedupRows,
  tableName: "DedupCheckTable",
  formats: { 4: "#,##0", 5: "#,##0", 6: "#,##0", 7: "#,##0", 8: "#,##0", 9: "#,##0", 10: "#,##0", 11: "#,##0", 12: "#,##0", 13: "#,##0.00", 14: "#,##0.00", 15: "#,##0.00", 16: "#,##0.00", 17: "#,##0.00", 18: "#,##0.00" },
  widths: { 0: 24, 1: 34, 2: 24, 3: 14 },
});
if (dedupRows.length) {
  dedupSheet.getRange(`D4:D${dedupRows.length + 3}`).conditionalFormats.add("containsText", {
    text: "WARNING",
    format: { fill: COLORS.amberLight, font: { bold: true, color: COLORS.amber } },
  });
  dedupSheet.getRange(`D4:D${dedupRows.length + 3}`).conditionalFormats.add("containsText", {
    text: "PASS",
    format: { fill: COLORS.greenLight, font: { bold: true, color: COLORS.green } },
  });
}

const histCampaignCount = addMetricSheet({ sheetName: "02_HIST_CAMPAIGN", title: "02｜历史Campaign聚合", subtitle: "来自30天搜索词每日明细，仅包含主ASIN关联Campaign；D3/D7/D14/D30均由30天事实源切片。", rows: payload.historical_metrics.campaign, tableName: "HistCampaignTable" });
addMetricSheet({ sheetName: "03_HIST_TARGET", title: "03｜历史Target聚合", subtitle: "名称键分析；缺少Amazon Target ID和当前Bid，禁止形成执行动作。", rows: payload.historical_metrics.target, tableName: "HistTargetTable" });
addMetricSheet({ sheetName: "04_HIST_SEARCH_TERM", title: "04｜历史搜索词聚合", subtitle: "按Campaign、Ad Group、Target、匹配类型和完整搜索词去重聚合。", rows: payload.historical_metrics.search_term, tableName: "HistSearchTermTable" });
addMetricSheet({ sheetName: "05_HIST_PLACEMENT", title: "05｜历史广告位聚合", subtitle: "广告位与Target是不同粒度，本表不与Target或商品表横向求和。", rows: payload.historical_metrics.placement, tableName: "HistPlacementTable" });
const histProductCount = addMetricSheet({ sheetName: "06_HIST_PRODUCT", title: "06｜历史广告商品聚合", subtitle: "主ASIN商品粒度是历史产品KPI事实源。", rows: payload.historical_metrics.product, tableName: "HistProductTable" });
addMetricSheet({ sheetName: "07_CURR_CAMPAIGN", title: "07｜当前短周期Campaign聚合", subtitle: "来自老品工作簿搜索词报告；当前只有短周期，不得当作成熟D7/D14/D30。", rows: payload.current_metrics.campaign, tableName: "CurrentCampaignTable" });
addMetricSheet({ sheetName: "08_CURR_TARGET", title: "08｜当前短周期Target聚合", subtitle: "名称键分析；自动投放对象与关键词字段保持原始语义，不补造Target ID。", rows: payload.current_metrics.target, tableName: "CurrentTargetTable" });
addMetricSheet({ sheetName: "09_CURR_SEARCH_TERM", title: "09｜当前短周期搜索词聚合", subtitle: "来自老品工作簿逐日搜索词报告，不使用含总计行的二次汇总表。", rows: payload.current_metrics.search_term, tableName: "CurrentSearchTermTable" });
addMetricSheet({ sheetName: "10_CURR_PLACEMENT", title: "10｜当前短周期广告位聚合", subtitle: "只观察位置表现；缺少可比Target×Placement证据时不生成基础Bid或Placement强动作。", rows: payload.current_metrics.placement, tableName: "CurrentPlacementTable" });
const currProductCount = addMetricSheet({ sheetName: "11_CURR_PRODUCT", title: "11｜当前短周期广告商品聚合", subtitle: "广告销售/广告订单与店铺销售/店铺订单口径分离；本表只聚合广告归因指标。", rows: payload.current_metrics.product, tableName: "CurrentProductTable" });

const storeRows = payload.current_store_metrics.map((row) => [
  row.asin,
  row.sku,
  toDate(row.period_start),
  toDate(row.period_end),
  toNumber(row.store_orders),
  toNumber(row.store_sales),
  row.source_grain,
]);
addTable({
  sheetName: "11B_CURR_STORE",
  title: "11B｜当前短周期店铺口径指标",
  subtitle: "店铺订单/销售额来自老品广告商品报告，但不属于广告归因指标；仅独立展示，不进入CVR、CPA或ACOS。",
  headers: ["asin", "sku", "period_start", "period_end", "store_orders", "store_sales", "source_grain"],
  rows: storeRows,
  tableName: "CurrentStoreMetricTable",
  formats: { 2: "yyyy-mm-dd", 3: "yyyy-mm-dd", 4: "#,##0", 5: "#,##0.00" },
  widths: { 0: 18, 1: 34, 2: 14, 3: 14, 4: 16, 5: 16, 6: 42 },
});

const settingsHeaders = ["period_label", "local_campaign_id", "campaign", "ad_group", "status", "daily_budget", "default_bid", "targeting_type", "bidding_strategy", "identity_quality"];
const settingsRows = payload.settings.map((row) => [
  row.period_label, row.local_campaign_id, row.campaign, row.ad_group || "", row.status,
  row.daily_budget === null ? null : toNumber(row.daily_budget),
  row.default_bid === null ? null : toNumber(row.default_bid),
  row.targeting_type, row.bidding_strategy, row.identity_quality,
]);
addTable({
  sheetName: "12_SETTINGS",
  title: "12｜Campaign设置与预算",
  subtitle: "历史来源只有Campaign级设置；当前来源是人工老品设置表。缺失字段保持缺失，不用CPC反推Bid。",
  headers: settingsHeaders,
  rows: settingsRows,
  tableName: "SettingsTable",
  formats: { 5: "#,##0.00", 6: "#,##0.00" },
  widths: { 0: 24, 1: 34, 2: 50, 3: 48, 4: 18, 5: 16, 6: 16, 7: 20, 8: 26, 9: 34 },
});

const issueRows = payload.issues.map((row) => [row.level, row.code, row.message]);
const issuesSheet = addTable({
  sheetName: "13_ISSUES",
  title: "13｜数据质量与使用限制",
  subtitle: "BLOCK_EXECUTION表示可以分析但不能形成Amazon后台动作；BLOCK_RULE_CALIBRATION表示数据不足以维护正式阈值。",
  headers: ["level", "code", "message"],
  rows: issueRows,
  tableName: "IssuesTable",
  widths: { 0: 26, 1: 36, 2: 110 },
});
if (issueRows.length) {
  issuesSheet.getRange(`A4:A${issueRows.length + 3}`).conditionalFormats.add("containsText", {
    text: "BLOCK",
    format: { fill: COLORS.redLight, font: { bold: true, color: COLORS.red } },
  });
  issuesSheet.getRange(`A4:A${issueRows.length + 3}`).conditionalFormats.add("containsText", {
    text: "WARNING",
    format: { fill: COLORS.amberLight, font: { bold: true, color: COLORS.amber } },
  });
}

const evidenceRows = payload.evidence.map((row) => [
  row.role, row.file_name, row.worksheet, row.row_count,
  toDate(row.period_start), toDate(row.period_end), row.sha256, row.source_path,
]);
addTable({
  sheetName: "14_EVIDENCE",
  title: "14｜来源证据索引",
  subtitle: "原始文件不修改；记录文件路径、工作表、行数、周期和SHA-256。",
  headers: ["role", "file_name", "worksheet", "row_count", "period_start", "period_end", "sha256", "source_path"],
  rows: evidenceRows,
  tableName: "EvidenceTable",
  formats: { 3: "#,##0", 4: "yyyy-mm-dd", 5: "yyyy-mm-dd" },
  widths: { 0: 34, 1: 46, 2: 30, 3: 14, 4: 14, 5: 14, 6: 68, 7: 70 },
});

const summary = workbook.worksheets.getItem("00_SUMMARY");
titleBand(
  summary,
  "陆遥广告智能体 V2.0｜5765广告数据聚合",
  "30天每日明细去重事实源 + 老品当前短周期；本包可用于人工分析，因缺Amazon不可变ID而禁止后台执行。",
  "J",
);
summary.getRange("A4:B12").values = [
  ["Data Snapshot ID", payload.data_snapshot_id],
  ["主ASIN", payload.primary_asin],
  ["分析状态", payload.analysis_status],
  ["执行状态", payload.execution_status],
  ["历史周期", `${payload.periods.historical.start} 至 ${payload.periods.historical.end}`],
  ["当前周期", `${payload.periods.current.start} 至 ${payload.periods.current.end}`],
  ["中间空档", `${payload.periods.gap_days} 天`],
  ["历史Campaign", payload.selected_historical_campaigns.length],
  ["去重规则", payload.deduplication_rule],
];
summary.getRange("A4:A12").format = { fill: COLORS.grayLight, font: { bold: true, color: COLORS.gray } };
summary.getRange("B4:B12").format = { borders: { preset: "outside", style: "thin", color: COLORS.border }, wrapText: true };
summary.getRange("A4:A12").format.columnWidth = 20;
summary.getRange("B4:B12").format.columnWidth = 62;
summary.getRange("B6").format = { fill: COLORS.amberLight, font: { bold: true, color: COLORS.amber } };
summary.getRange("B7").format = { fill: COLORS.redLight, font: { bold: true, color: COLORS.red } };

summary.getRange("D4:F4").values = [["指标", "历史30天", `当前${payload.periods.current.days}天`]];
summary.getRange("D4:F4").format = { fill: COLORS.blue, font: { bold: true, color: COLORS.white } };
summary.getRange("D5:D14").values = [
  ["曝光"], ["点击"], ["广告订单"], ["广告花费"], ["广告销售额"],
  ["CTR"], ["CVR"], ["CPA"], ["ACOS"], ["日均花费"],
];
summary.getRange("D5:D14").format = { fill: COLORS.blueLight, font: { bold: true, color: COLORS.navy } };
summary.getRange("D4:D14").format.columnWidth = 18;
summary.getRange("E4:F14").format.columnWidth = 18;

const histEnd = histProductCount + 3;
const currEnd = currProductCount + 3;
const primary = payload.primary_asin;
const histWindow = "D30";
const currWindow = `CURRENT_${payload.periods.current.days}D`;
const matchingRows = (rows, windowName) => rows
  .map((row, index) => ({ row, excelRow: index + 4 }))
  .filter(({ row }) => row.object_label.includes(primary) && row.window === windowName)
  .map(({ excelRow }) => excelRow);
const sumCells = (sheetName, sourceColumn, excelRows) => {
  if (!excelRows.length) return "=0";
  return `=${excelRows.map((row) => `'${sheetName}'!${sourceColumn}${row}`).join("+")}`;
};
const histMatchRows = matchingRows(payload.historical_metrics.product, histWindow);
const currMatchRows = matchingRows(payload.current_metrics.product, currWindow);
for (const [column, sheetName, excelRows, days] of [
  ["E", "06_HIST_PRODUCT", histMatchRows, payload.periods.historical.days],
  ["F", "11_CURR_PRODUCT", currMatchRows, payload.periods.current.days],
]) {
  summary.getRange(`${column}5:${column}9`).formulas = [
    [sumCells(sheetName, "J", excelRows)],
    [sumCells(sheetName, "K", excelRows)],
    [sumCells(sheetName, "L", excelRows)],
    [sumCells(sheetName, "M", excelRows)],
    [sumCells(sheetName, "N", excelRows)],
  ];
  summary.getRange(`${column}10:${column}14`).formulas = [
    [`=IF(${column}5=0,"",${column}6/${column}5)`],
    [`=IF(${column}6=0,"",${column}7/${column}6)`],
    [`=IF(${column}7=0,"",${column}8/${column}7)`],
    [`=IF(${column}9=0,"",${column}8/${column}9)`],
    [`=${column}8/${days}`],
  ];
}
summary.getRange("E5:F7").format.numberFormat = "#,##0";
summary.getRange("E8:F9").format.numberFormat = "#,##0.00";
summary.getRange("E10:F11").format.numberFormat = "0.00%";
summary.getRange("E12:F12").format.numberFormat = "#,##0.00";
summary.getRange("E13:F13").format.numberFormat = "0.00%";
summary.getRange("E14:F14").format.numberFormat = "#,##0.00";
summary.getRange("D16:F20").values = [
  ["使用结论", "状态", "说明"],
  ["30天事实源", "可分析", "所有D3/D7/D14/D30均从30天每日明细切片"],
  ["7/14天文件", "不累加", "只用于校验窗口一致性"],
  ["当前短周期", "观察", "周期不足，不能直接判稳定、放量或停止"],
  ["Amazon动作", "阻断", "缺Campaign/Ad Group/Target不可变ID"],
];
summary.getRange("D16:F16").format = { fill: COLORS.gray, font: { bold: true, color: COLORS.white } };
summary.getRange("D17:F20").format.wrapText = true;
summary.getRange("D16:D20").format.columnWidth = 20;
summary.getRange("E16:E20").format.columnWidth = 16;
summary.getRange("F16:F20").format.columnWidth = 52;
summary.getRange("H4:J4").values = [["当前店铺口径", "数值", "是否进入广告效率"]];
summary.getRange("H4:J4").format = { fill: COLORS.teal, font: { bold: true, color: COLORS.white } };
summary.getRange("H5:H6").values = [["店铺订单"], ["店铺销售额"]];
summary.getRange("I5:I6").formulas = [
  [`=SUM('11B_CURR_STORE'!E4:E${storeRows.length + 3})`],
  [`=SUM('11B_CURR_STORE'!F4:F${storeRows.length + 3})`],
];
summary.getRange("J5:J6").values = [["否"], ["否"]];
summary.getRange("H5:H6").format = { fill: COLORS.blueLight, font: { bold: true, color: COLORS.navy } };
summary.getRange("I5").format.numberFormat = "#,##0";
summary.getRange("I6").format.numberFormat = "#,##0.00";
summary.getRange("H4:H6").format.columnWidth = 20;
summary.getRange("I4:I6").format.columnWidth = 16;
summary.getRange("J4:J6").format.columnWidth = 22;
summary.freezePanes.freezeRows(2);

const formulaErrorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
if ((formulaErrorScan.ndjson || "").includes("#REF!") || (formulaErrorScan.ndjson || "").includes("#DIV/0!")) {
  throw new Error(`Workbook formula errors: ${formulaErrorScan.ndjson}`);
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  const inspect = await workbook.inspect({
    kind: "workbook,sheet,table,formula",
    maxChars: 18000,
    tableMaxRows: 6,
    tableMaxCols: 12,
    options: { maxResults: 300 },
  });
  await fs.writeFile(path.join(previewDir, "workbook_inspect.ndjson"), inspect.ndjson || String(inspect), "utf8");
  const previewRanges = {
    "00_SUMMARY": "A1:J20",
    "01_DEDUP_CHECK": "A1:S20",
    "02_HIST_CAMPAIGN": "A1:U20",
    "03_HIST_TARGET": "A1:U30",
    "04_HIST_SEARCH_TERM": "A1:U30",
    "05_HIST_PLACEMENT": "A1:U30",
    "06_HIST_PRODUCT": "A1:U20",
    "07_CURR_CAMPAIGN": "A1:U15",
    "08_CURR_TARGET": "A1:U20",
    "09_CURR_SEARCH_TERM": "A1:U30",
    "10_CURR_PLACEMENT": "A1:U20",
    "11_CURR_PRODUCT": "A1:U15",
    "11B_CURR_STORE": "A1:G15",
    "12_SETTINGS": "A1:J20",
    "13_ISSUES": "A1:C30",
    "14_EVIDENCE": "A1:H35",
  };
  for (const sheetName of sheetNames) {
    const preview = await workbook.render({
      sheetName,
      range: previewRanges[sheetName],
      scale: 1,
      format: "png",
    });
    await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
