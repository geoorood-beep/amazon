import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

const [payloadPath, outputPath, previewDir] = process.argv.slice(2);
if (!payloadPath || !outputPath) {
  throw new Error("Usage: workbook_builder.mjs <payload.json> <output.xlsx> [preview_dir]");
}

const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const workbook = Workbook.create();

const COLORS = {
  blue: "#0B5CAD",
  blueDark: "#073B6F",
  blueLight: "#DCEEFF",
  green: "#1F7A4D",
  greenLight: "#E5F5EC",
  amber: "#A86100",
  amberLight: "#FFF3D6",
  red: "#B42318",
  redLight: "#FDE7E5",
  gray: "#5B6675",
  grayLight: "#EEF1F5",
  white: "#FFFFFF",
  border: "#C9D2DE",
  text: "#17202A",
};

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
    fill: COLORS.blueDark,
    font: { bold: true, color: COLORS.white, size: 16 },
    rowHeight: 30,
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${endColumn}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${endColumn}2`).format = {
    fill: COLORS.blueLight,
    font: { color: COLORS.blueDark, italic: true },
    rowHeight: 24,
    verticalAlignment: "center",
  };
};

const addTableSheet = ({
  name,
  title,
  subtitle,
  headers,
  rows,
  tableName,
  formats = {},
  widths = {},
}) => {
  const sheet = workbook.worksheets.getItem(name);
  const endColumn = columnName(Math.max(headers.length - 1, 7));
  titleBand(sheet, title, subtitle, endColumn);
  sheet.getRangeByIndexes(2, 0, 1, headers.length).values = [headers];
  sheet.getRangeByIndexes(2, 0, 1, headers.length).format = {
    fill: COLORS.blue,
    font: { bold: true, color: COLORS.white },
    rowHeight: 24,
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: COLORS.blueDark },
  };
  if (rows.length) {
    sheet.getRangeByIndexes(3, 0, rows.length, headers.length).values = rows;
    const table = sheet.tables.add(
      `A3:${columnName(headers.length - 1)}${rows.length + 3}`,
      true,
      tableName,
    );
    table.style = "TableStyleMedium2";
    table.showFilterButton = true;
  } else {
    sheet.getRangeByIndexes(3, 0, 1, headers.length).values = [
      ["无数据", ...Array(headers.length - 1).fill(null)],
    ];
    sheet.getRangeByIndexes(3, 0, 1, headers.length).format = {
      fill: COLORS.amberLight,
      font: { color: COLORS.amber },
    };
  }
  const populatedRows = Math.max(rows.length, 1);
  for (const [indexText, format] of Object.entries(formats)) {
    const index = Number(indexText);
    sheet.getRangeByIndexes(3, index, populatedRows, 1).format.numberFormat = format;
  }
  for (let index = 0; index < headers.length; index += 1) {
    const width = widths[index] ?? Math.min(Math.max(headers[index].length + 4, 12), 28);
    sheet.getRangeByIndexes(0, index, populatedRows + 3, 1).format.columnWidth = width;
  }
  sheet.getRangeByIndexes(3, 0, populatedRows, headers.length).format = {
    verticalAlignment: "center",
  };
  sheet.freezePanes.freezeRows(3);
  return sheet;
};

// Create every worksheet before formulas or cross-sheet chart references.
const snapshot = workbook.worksheets.add("00_SNAPSHOT");
const agentInput = workbook.worksheets.add("01_AGENT_INPUT");
const reconciliation = workbook.worksheets.add("02_RECONCILIATION");
const evidence = workbook.worksheets.add("03_EVIDENCE_INDEX");
const campaigns = workbook.worksheets.add("04_CAMPAIGNS");
const adGroups = workbook.worksheets.add("05_AD_GROUPS");
const targets = workbook.worksheets.add("06_TARGETS");
const searchTerms = workbook.worksheets.add("07_SEARCH_TERMS");
const issues = workbook.worksheets.add("08_ISSUES");
const daily = workbook.worksheets.add("09_DAILY_TOTALS");

titleBand(
  snapshot,
  "陆遥广告智能体 V2.0｜广告报表聚合快照",
  "本工作簿只做本地聚合、数据质量与证据追溯；Amazon 后台动作执行保持关闭。",
  "N",
);
snapshot.showGridLines = false;
snapshot.getRange("A4:B11").values = [
  ["数据质量", payload.dq_report.status],
  ["对账状态", payload.packet.metadata.reconciliation_status],
  ["Data Snapshot ID", payload.packet.metadata.data_snapshot_id],
  ["观察周期", `${payload.packet.metadata.period_start} 至 ${payload.packet.metadata.period_end}`],
  ["站点 / 币种", `${payload.packet.metadata.marketplace} / ${payload.packet.metadata.currency}`],
  ["来源报表数", payload.packet.report_sources.length],
  ["有效指标行", payload.agent_input_rows.length],
  ["导入问题数", payload.dq_report.findings.length],
];
snapshot.getRange("A4:A11").format = {
  fill: COLORS.grayLight,
  font: { bold: true, color: COLORS.gray },
};
snapshot.getRange("B4:B11").format = {
  fill: COLORS.white,
  font: { bold: true, color: COLORS.text },
  borders: { preset: "outside", style: "thin", color: COLORS.border },
};
snapshot.getRange("A4:B11").format.rowHeight = 24;
snapshot.getRange("A4:A11").format.columnWidth = 20;
snapshot.getRange("B4:B11").format.columnWidth = 34;

snapshot.getRange("D4:E10").values = [
  ["30日曝光", null],
  ["30日点击", null],
  ["30日订单", null],
  ["30日花费", null],
  ["30日销售额", null],
  ["30日 ACOS", null],
  ["30日 ROAS", null],
];
snapshot.getRange("D4:D10").format = {
  fill: COLORS.blueLight,
  font: { bold: true, color: COLORS.blueDark },
};
snapshot.getRange("E4:E10").format = {
  fill: COLORS.white,
  font: { bold: true, color: COLORS.text },
  borders: { preset: "outside", style: "thin", color: COLORS.border },
};
snapshot.getRange("D4:E10").format.rowHeight = 24;
snapshot.getRange("D4:D10").format.columnWidth = 16;
snapshot.getRange("E4:E10").format.columnWidth = 16;

const agentHeaders = [
  "data_snapshot_id",
  "object_type",
  "object_id",
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
];
titleBand(
  agentInput,
  "01｜智能体唯一聚合输入表",
  "不同 object_type / window 保持独立粒度，禁止跨粒度直接相加；比率列由工作簿公式计算。",
  "R",
);
agentInput.getRange("A3:R3").values = [agentHeaders];
agentInput.getRange("A3:R3").format = {
  fill: COLORS.blue,
  font: { bold: true, color: COLORS.white },
  rowHeight: 30,
  wrapText: true,
  verticalAlignment: "center",
};
const inputRows = payload.agent_input_rows.map((row) => [
  row.data_snapshot_id,
  row.object_type,
  row.object_id,
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
]);
if (inputRows.length) {
  agentInput.getRangeByIndexes(3, 0, inputRows.length, agentHeaders.length).values = inputRows;
  const formulaRows = inputRows.map((_, index) => {
    const row = index + 4;
    return [
      `=IF(H${row}=0,"",I${row}/H${row})`,
      `=IF(I${row}=0,"",J${row}/I${row})`,
      `=IF(I${row}=0,"",K${row}/I${row})`,
      `=IF(J${row}=0,"",K${row}/J${row})`,
      `=IF(L${row}=0,"",K${row}/L${row})`,
      `=IF(K${row}=0,"",L${row}/K${row})`,
    ];
  });
  agentInput.getRangeByIndexes(3, 12, formulaRows.length, 6).formulas = formulaRows;
  const table = agentInput.tables.add(`A3:R${inputRows.length + 3}`, true, "AgentInputTable");
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
} else {
  agentInput.getRange("A4:R4").values = [["无有效聚合数据", ...Array(17).fill(null)]];
  agentInput.getRange("A4:R4").format.fill = COLORS.redLight;
}
agentInput.getRange(`F4:G${Math.max(inputRows.length + 3, 4)}`).format.numberFormat = "yyyy-mm-dd";
agentInput.getRange(`H4:J${Math.max(inputRows.length + 3, 4)}`).format.numberFormat = "#,##0";
agentInput.getRange(`K4:L${Math.max(inputRows.length + 3, 4)}`).format.numberFormat = "#,##0.00";
agentInput.getRange(`M4:N${Math.max(inputRows.length + 3, 4)}`).format.numberFormat = "0.0%";
agentInput.getRange(`O4:P${Math.max(inputRows.length + 3, 4)}`).format.numberFormat = "#,##0.00";
agentInput.getRange(`Q4:Q${Math.max(inputRows.length + 3, 4)}`).format.numberFormat = "0.0%";
agentInput.getRange(`R4:R${Math.max(inputRows.length + 3, 4)}`).format.numberFormat = "0.00x";
const inputWidths = [24, 20, 26, 46, 10, 12, 12, 12, 10, 10, 12, 12, 10, 10, 10, 10, 10, 10];
inputWidths.forEach((width, index) => {
  agentInput.getRangeByIndexes(0, index, Math.max(inputRows.length + 3, 4), 1).format.columnWidth = width;
});
agentInput.freezePanes.freezeRows(3);
agentInput.freezePanes.freezeColumns(4);

const reconHeaders = [
  "campaign_id",
  "ad_group_id",
  "target_id",
  "search_term",
  "metric",
  "daily_value",
  "summary_value",
  "difference",
  "technical_tolerance",
  "status",
];
const reconRows = payload.reconciliation_rows.map((row) => [
  row.campaign_id,
  row.ad_group_id,
  row.target_id,
  row.search_term,
  row.metric,
  toNumber(row.daily_value),
  toNumber(row.summary_value),
  toNumber(row.difference),
  toNumber(row.tolerance),
  row.status,
]);
const reconSheet = addTableSheet({
  name: "02_RECONCILIATION",
  title: "02｜搜索词每日明细 × 汇总对账",
  subtitle: "金额容差仅处理二位小数舍入；这不是广告业务阈值。任一 BLOCKED 会阻断分析入口。",
  headers: reconHeaders,
  rows: reconRows,
  tableName: "ReconciliationTable",
  formats: { 5: "#,##0.00", 6: "#,##0.00", 7: "#,##0.00", 8: "#,##0.00" },
  widths: { 0: 18, 1: 18, 2: 18, 3: 34, 4: 14, 8: 20, 9: 14 },
});
if (reconRows.length) {
  reconSheet
    .getRange(`J4:J${reconRows.length + 3}`)
    .conditionalFormats.add("containsText", {
      text: "BLOCKED",
      format: { fill: COLORS.redLight, font: { bold: true, color: COLORS.red } },
    });
}

const evidenceHeaders = [
  "report_type",
  "file_name",
  "worksheet",
  "row_count",
  "period_start",
  "period_end",
  "sha256",
  "source_path",
];
const loadedReportByName = new Map(
  Object.values(payload.loaded_reports).map((item) => [path.basename(item.path), item]),
);
const evidenceRows = payload.packet.report_sources.map((source) => {
  const loaded = loadedReportByName.get(source.file_name) || {};
  return [
    source.report_type,
    source.file_name,
    source.worksheet || "",
    source.row_count,
    toDate(source.period_start),
    toDate(source.period_end),
    source.sha256,
    loaded.path || "",
  ];
});
addTableSheet({
  name: "03_EVIDENCE_INDEX",
  title: "03｜证据与来源索引",
  subtitle: "源文件保持原样；本表记录文件、工作表、周期、有效行数和 SHA-256。",
  headers: evidenceHeaders,
  rows: evidenceRows,
  tableName: "EvidenceIndexTable",
  formats: { 4: "yyyy-mm-dd", 5: "yyyy-mm-dd" },
  widths: { 0: 24, 1: 34, 2: 18, 3: 12, 4: 12, 5: 12, 6: 66, 7: 54 },
});

addTableSheet({
  name: "04_CAMPAIGNS",
  title: "04｜Campaign 结构事实",
  subtitle: "来自 Campaign / Ad Group 设置表；不含动作建议。",
  headers: ["campaign_id", "campaign_name", "daily_budget", "status"],
  rows: payload.packet.campaigns.map((row) => [
    row.campaign_id,
    row.campaign_name,
    toNumber(row.daily_budget),
    row.status,
  ]),
  tableName: "CampaignFactsTable",
  formats: { 2: "#,##0.00" },
  widths: { 0: 22, 1: 38, 2: 16, 3: 16 },
});

addTableSheet({
  name: "05_AD_GROUPS",
  title: "05｜Ad Group 结构事实",
  subtitle: "V2.0 当前完整模式要求一个 Campaign 恰好对应一个 Ad Group。",
  headers: ["ad_group_id", "campaign_id", "ad_group_name", "default_bid", "status"],
  rows: payload.packet.ad_groups.map((row) => [
    row.ad_group_id,
    row.campaign_id,
    row.ad_group_name,
    row.default_bid === null ? null : toNumber(row.default_bid),
    row.status,
  ]),
  tableName: "AdGroupFactsTable",
  formats: { 3: "#,##0.00" },
  widths: { 0: 22, 1: 22, 2: 38, 3: 16, 4: 16 },
});

addTableSheet({
  name: "06_TARGETS",
  title: "06｜Target / Keyword 结构事实",
  subtitle: "Target ID、父级链、匹配类型、当前 Bid 和状态来自投放对象报表。",
  headers: [
    "target_id",
    "campaign_id",
    "ad_group_id",
    "target_text",
    "match_type",
    "bid",
    "status",
  ],
  rows: payload.packet.targets.map((row) => [
    row.target_id,
    row.campaign_id,
    row.ad_group_id,
    row.target_text,
    row.match_type,
    toNumber(row.bid),
    row.status,
  ]),
  tableName: "TargetFactsTable",
  formats: { 5: "#,##0.00" },
  widths: { 0: 22, 1: 22, 2: 22, 3: 42, 4: 16, 5: 14, 6: 16 },
});

addTableSheet({
  name: "07_SEARCH_TERMS",
  title: "07｜搜索词父级链事实",
  subtitle: "search_term_key 为本地稳定哈希键；同一搜索词在不同父级链下不会被混为一行。",
  headers: [
    "search_term_key",
    "campaign_id",
    "ad_group_id",
    "target_id",
    "search_term",
  ],
  rows: payload.packet.search_terms.map((row) => [
    row.search_term_key,
    row.campaign_id,
    row.ad_group_id,
    row.target_id || "",
    row.search_term,
  ]),
  tableName: "SearchTermFactsTable",
  widths: { 0: 26, 1: 22, 2: 22, 3: 22, 4: 42 },
});

const issueRows = payload.dq_report.findings.map((row) => [
  row.level,
  row.code,
  row.object_id || "",
  row.message,
]);
const issueSheet = addTableSheet({
  name: "08_ISSUES",
  title: "08｜数据质量问题",
  subtitle: "BLOCK 必须先修复；APPROVAL 需要人工确认。AUTO_PASS 不代表 Amazon 后台已执行。",
  headers: ["level", "code", "object_id", "message"],
  rows: issueRows,
  tableName: "DataQualityIssuesTable",
  widths: { 0: 14, 1: 34, 2: 24, 3: 80 },
});
if (issueRows.length) {
  issueSheet
    .getRange(`A4:A${issueRows.length + 3}`)
    .conditionalFormats.add("containsText", {
      text: "BLOCK",
      format: { fill: COLORS.redLight, font: { bold: true, color: COLORS.red } },
    });
  issueSheet
    .getRange(`A4:A${issueRows.length + 3}`)
    .conditionalFormats.add("containsText", {
      text: "APPROVAL",
      format: { fill: COLORS.amberLight, font: { bold: true, color: COLORS.amber } },
    });
}

const dailyRows = payload.daily_totals.map((row) => [
  toDate(row.date),
  String(row.date).slice(0, 10),
  toNumber(row.impressions),
  toNumber(row.clicks),
  toNumber(row.orders),
  toNumber(row.spend),
  toNumber(row.sales),
]);
addTableSheet({
  name: "09_DAILY_TOTALS",
  title: "09｜每日账户聚合趋势",
  subtitle: "只汇总搜索词每日明细，不与 Target、Placement 或商品报表重复相加。",
  headers: ["date", "date_label", "impressions", "clicks", "orders", "spend", "sales"],
  rows: dailyRows,
  tableName: "DailyTotalsTable",
  formats: { 0: "yyyy-mm-dd", 2: "#,##0", 3: "#,##0", 4: "#,##0", 5: "#,##0.00", 6: "#,##0.00" },
  widths: { 0: 14, 1: 14, 2: 16, 3: 14, 4: 14, 5: 16, 6: 16 },
});

const dailyEndRow = dailyRows.length + 3;
if (dailyRows.length) {
  snapshot.getRange("E4:E8").formulas = [
    [`=SUM('09_DAILY_TOTALS'!C4:C${dailyEndRow})`],
    [`=SUM('09_DAILY_TOTALS'!D4:D${dailyEndRow})`],
    [`=SUM('09_DAILY_TOTALS'!E4:E${dailyEndRow})`],
    [`=SUM('09_DAILY_TOTALS'!F4:F${dailyEndRow})`],
    [`=SUM('09_DAILY_TOTALS'!G4:G${dailyEndRow})`],
  ];
  snapshot.getRange("E9").formulas = [["=IF(E8=0,\"\",E7/E8)"]];
  snapshot.getRange("E10").formulas = [["=IF(E7=0,\"\",E8/E7)"]];
  snapshot.getRange("E4:E6").format.numberFormat = "#,##0";
  snapshot.getRange("E7:E8").format.numberFormat = "#,##0.00";
  snapshot.getRange("E9").format.numberFormat = "0.0%";
  snapshot.getRange("E10").format.numberFormat = "0.00x";

  const chart = snapshot.charts.add("line", {
    chartType: "line",
    title: "每日花费与销售额",
    hasLegend: true,
  });
  const spendSeries = chart.series.add("Spend");
  spendSeries.categoryFormula = `'09_DAILY_TOTALS'!$B$4:$B$${dailyEndRow}`;
  spendSeries.formula = `'09_DAILY_TOTALS'!$F$4:$F$${dailyEndRow}`;
  spendSeries.fill = COLORS.red;
  const salesSeries = chart.series.add("Sales");
  salesSeries.categoryFormula = `'09_DAILY_TOTALS'!$B$4:$B$${dailyEndRow}`;
  salesSeries.formula = `'09_DAILY_TOTALS'!$G$4:$G$${dailyEndRow}`;
  salesSeries.fill = COLORS.blue;
  chart.title = "每日花费与销售额";
  chart.hasLegend = true;
  chart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
  chart.yAxis = { numberFormatCode: "#,##0.00" };
  chart.setPosition("G4", "N18");
}

snapshot.getRange("A14:E17").values = [
  ["颜色说明", "含义", null, null, null],
  ["绿色", "DQ_PASS / 对账通过", null, null, null],
  ["黄色", "需要人工确认", null, null, null],
  ["红色", "阻断，禁止进入广告判断", null, null, null],
];
snapshot.getRange("A14:E14").format = {
  fill: COLORS.gray,
  font: { bold: true, color: COLORS.white },
};
snapshot.getRange("A15").format.fill = COLORS.greenLight;
snapshot.getRange("A16").format.fill = COLORS.amberLight;
snapshot.getRange("A17").format.fill = COLORS.redLight;
snapshot.getRange("A14:A17").format.columnWidth = 18;
snapshot.getRange("B14:B17").format.columnWidth = 34;
snapshot.freezePanes.freezeRows(2);

if (payload.dq_report.status === "DQ_PASS") {
  snapshot.getRange("B4").format = {
    fill: COLORS.greenLight,
    font: { bold: true, color: COLORS.green },
  };
} else if (payload.dq_report.status === "DQ_BLOCKED") {
  snapshot.getRange("B4").format = {
    fill: COLORS.redLight,
    font: { bold: true, color: COLORS.red },
  };
} else {
  snapshot.getRange("B4").format = {
    fill: COLORS.amberLight,
    font: { bold: true, color: COLORS.amber },
  };
}

const formulaErrors = [];
const errorTokens = ["#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A"];
for (const sheetName of ["00_SNAPSHOT", "01_AGENT_INPUT"]) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const used = sheet.getUsedRange();
  const values = used ? used.values : [];
  for (let rowIndex = 0; rowIndex < values.length; rowIndex += 1) {
    for (let colIndex = 0; colIndex < values[rowIndex].length; colIndex += 1) {
      const value = values[rowIndex][colIndex];
      if (typeof value === "string" && errorTokens.some((token) => value.includes(token))) {
        formulaErrors.push(`${sheetName}!${columnName(colIndex)}${rowIndex + 1}=${value}`);
      }
    }
  }
}
if (formulaErrors.length) {
  throw new Error(`Workbook formula errors: ${formulaErrors.join(", ")}`);
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  const inspect = await workbook.inspect({
    kind: "workbook,sheet,table,formula",
    maxChars: 12000,
    tableMaxRows: 8,
    tableMaxCols: 12,
    options: { maxResults: 200 },
  });
  await fs.writeFile(
    path.join(previewDir, "workbook_inspect.ndjson"),
    inspect.ndjson || String(inspect),
    "utf8",
  );
  for (const sheetName of [
    "00_SNAPSHOT",
    "01_AGENT_INPUT",
    "02_RECONCILIATION",
    "03_EVIDENCE_INDEX",
    "04_CAMPAIGNS",
    "05_AD_GROUPS",
    "06_TARGETS",
    "07_SEARCH_TERMS",
    "08_ISSUES",
    "09_DAILY_TOTALS",
  ]) {
    const preview = await workbook.render({
      sheetName,
      autoCrop: "all",
      scale: 1,
      format: "png",
    });
    await fs.writeFile(
      path.join(previewDir, `${sheetName}.png`),
      new Uint8Array(await preview.arrayBuffer()),
    );
  }
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
