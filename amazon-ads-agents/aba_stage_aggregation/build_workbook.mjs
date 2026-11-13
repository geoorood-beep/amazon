import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const inputPath = "aba_stage_aggregation/data/aggregation.json";
const outputPath = "/Users/leo/Desktop/地毯ABA阶段关键词聚合_门垫长条区域_表2_20260625.xlsx";
const previewDir = "aba_stage_aggregation/previews";

const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));

function colName(index) {
  let n = index + 1;
  let s = "";
  while (n > 0) {
    const m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = Math.floor((n - m) / 26);
  }
  return s;
}

function tableRange(rowCount, colCount, startRow = 1, startCol = 0) {
  const endRow = startRow + rowCount - 1;
  const start = `${colName(startCol)}${startRow}`;
  const end = `${colName(startCol + colCount - 1)}${endRow}`;
  return `${start}:${end}`;
}

function asRows(objects, columns) {
  return objects.map((obj) => columns.map((col) => obj[col.key] ?? ""));
}

function writeTable(sheet, title, columns, objects, tableName, options = {}) {
  sheet.showGridLines = false;
  sheet.getRange("A1").values = [[title]];
  const titleRange = sheet.getRangeByIndexes(0, 0, 1, columns.length);
  titleRange.merge();
  titleRange.format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF", size: 14 },
    horizontalAlignment: "left",
  };
  const header = columns.map((c) => c.label);
  const rows = asRows(objects, columns);
  const matrix = [header, ...rows];
  const startRow = 3;
  const range = sheet.getRange(tableRange(matrix.length, columns.length, startRow, 0));
  range.values = matrix;
  const headerRange = sheet.getRange(tableRange(1, columns.length, startRow, 0));
  headerRange.format = {
    fill: "#D9EAF7",
    font: { bold: true, color: "#1F2933" },
    wrapText: true,
    verticalAlignment: "center",
  };
  range.format.borders = { preset: "outside", style: "thin", color: "#B7C9D6" };
  range.format.wrapText = true;
  sheet.tables.add(tableRange(matrix.length, columns.length, startRow, 0), true, tableName).style = "TableStyleMedium2";
  sheet.freezePanes.freezeRows(startRow);
  columns.forEach((col, idx) => {
    const width = col.width ?? 18;
    sheet.getRange(`${colName(idx)}:${colName(idx)}`).format.columnWidth = width;
    if (col.numberFormat) {
      sheet.getRange(`${colName(idx)}${startRow + 1}:${colName(idx)}${startRow + Math.max(rows.length, 1)}`).format.numberFormat = col.numberFormat;
    }
  });
  if (options.note) {
    const noteRow = startRow + matrix.length + 2;
    sheet.getRangeByIndexes(noteRow - 1, 0, 1, columns.length).merge();
    sheet.getRange(`A${noteRow}`).values = [[options.note]];
    sheet.getRange(`A${noteRow}`).format = { fill: "#FFF4CC", font: { color: "#7A4D00" }, wrapText: true };
  }
}

function writeInfoSheet(sheet) {
  sheet.showGridLines = false;
  const rows = [
    ["地毯ABA阶段关键词聚合", ""],
    ["SOP来源", payload.sop.source_sop],
    ["ABA来源文件", payload.source.source_workbook],
    ["本次按“表2”解释为", `工作簿第二张工作表：${payload.source.source_sheet}`],
    ["ABA排名月份", payload.source.rank_month],
    ["表2有效关键词数", payload.source.usable_keyword_rows],
    ["新品命中明细行数", payload.new_product_detail.length],
    ["老品命中明细行数", payload.old_product_detail.length],
    ["已跳过圆形词行数", payload.skipped_round.length],
    ["重要限制", payload.notes.join("；")],
  ];
  sheet.getRange(tableRange(rows.length, 2, 1, 0)).values = rows;
  sheet.getRange("A1:B1").format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF", size: 14 },
  };
  sheet.getRange("A2:A10").format = { fill: "#D9EAF7", font: { bold: true } };
  sheet.getRange("A1:B10").format.borders = { preset: "all", style: "thin", color: "#B7C9D6" };
  sheet.getRange("A:A").format.columnWidth = 22;
  sheet.getRange("B:B").format.columnWidth = 95;
  sheet.getRange("B:B").format.wrapText = true;
}

const workbook = Workbook.create();

writeInfoSheet(workbook.worksheets.add("说明与口径"));

writeTable(
  workbook.worksheets.add("SOP阶段规则"),
  "SOP 4.3.2 新品 ABA 阶段规则",
  [
    { key: "stage", label: "订单阶段", width: 16 },
    { key: "area_min", label: "Area Rug最小ABA", width: 15, numberFormat: "#,##0" },
    { key: "area_max", label: "Area Rug最大ABA", width: 15, numberFormat: "#,##0" },
    { key: "runner_min", label: "Runner最小ABA", width: 15, numberFormat: "#,##0" },
    { key: "runner_max", label: "Runner最大ABA", width: 15, numberFormat: "#,##0" },
    { key: "keyword_types", label: "适合关键词类型", width: 34 },
    { key: "examples", label: "SOP示例", width: 44 },
    { key: "min_match_score", label: "最低匹配度", width: 12 },
    { key: "max_keyword_count", label: "最大选词数", width: 12 },
  ],
  payload.sop.stage_rules,
  "SOPStageRules",
);

writeTable(
  workbook.worksheets.add("新品阶段汇总"),
  "模块一：新品推广 - 阶段 × 产品类型可用关键词数量",
  [
    { key: "module", label: "模块", width: 18 },
    { key: "product_type", label: "产品类型", width: 28 },
    { key: "stage", label: "订单阶段", width: 14 },
    { key: "aba_range", label: "ABA区间", width: 16 },
    { key: "keyword_count", label: "关键词数", width: 12, numberFormat: "#,##0" },
  ],
  payload.new_product_summary,
  "NewProductSummary",
  { note: "注意：最大选词数是单个产品/广告架构的上限；本表列的是表2中按ABA区间命中的全部候选词数量。" },
);

writeTable(
  workbook.worksheets.add("新品可用关键词明细"),
  "模块一：新品推广 - 可用关键词明细",
  [
    { key: "module", label: "模块", width: 18 },
    { key: "product_type", label: "产品类型", width: 28 },
    { key: "aba_source", label: "ABA口径来源", width: 14 },
    { key: "stage", label: "订单阶段", width: 14 },
    { key: "aba_range", label: "ABA区间", width: 16 },
    { key: "keyword", label: "关键词", width: 36 },
    { key: "aba_rank", label: "ABA排名", width: 12, numberFormat: "#,##0" },
    { key: "rank_month", label: "排名月份", width: 10 },
    { key: "sop_keyword_types", label: "SOP适合关键词类型", width: 34 },
    { key: "min_match_score", label: "最低匹配度", width: 12 },
    { key: "max_keyword_count", label: "最大选词数", width: 12 },
    { key: "match_basis", label: "产品类型匹配依据", width: 56 },
  ],
  payload.new_product_detail,
  "NewKeywordDetail",
);

writeTable(
  workbook.worksheets.add("老品ABA动作汇总"),
  "模块二：老品推广 - ABA 10W 动作汇总",
  [
    { key: "module", label: "模块", width: 18 },
    { key: "product_type", label: "产品类型", width: 28 },
    { key: "stage_or_action", label: "SOP动作", width: 56 },
    { key: "keyword_count", label: "关键词数", width: 12, numberFormat: "#,##0" },
  ],
  payload.old_product_summary,
  "OldProductSummary",
  { note: "老品实际是否放大，还必须结合CPA/CVR/订单样本、词根整体效果和产品属性匹配，不只看ABA排名。" },
);

writeTable(
  workbook.worksheets.add("老品关键词明细"),
  "模块二：老品推广 - ABA结构动作关键词明细",
  [
    { key: "module", label: "模块", width: 18 },
    { key: "product_type", label: "产品类型", width: 28 },
    { key: "aba_source", label: "ABA口径来源", width: 14 },
    { key: "keyword", label: "关键词", width: 36 },
    { key: "aba_rank", label: "ABA排名", width: 12, numberFormat: "#,##0" },
    { key: "rank_month", label: "排名月份", width: 10 },
    { key: "old_product_action", label: "SOP动作", width: 58 },
    { key: "match_basis", label: "产品类型匹配依据", width: 56 },
  ],
  payload.old_product_detail,
  "OldKeywordDetail",
);

writeTable(
  workbook.worksheets.add("表2ABA源数据"),
  "表2 ABA 源数据 - 已去重有效行",
  [
    { key: "keyword", label: "关键词", width: 42 },
    { key: "aba_rank", label: "ABA排名", width: 12, numberFormat: "#,##0" },
    { key: "rank_month", label: "排名月份", width: 10 },
  ],
  payload.source_keywords,
  "SourceTable2ABA",
);

await fs.rm(previewDir, { recursive: true, force: true });
await fs.mkdir(previewDir, { recursive: true });
for (const sheet of workbook.worksheets.items) {
  const preview = await workbook.render({
    sheetName: sheet.name,
    range: "A1:L35",
    scale: 1,
    format: "png",
  });
  const previewPath = path.join(previewDir, `${sheet.name.replace(/[\\/:"*?<>|]/g, "_")}.png`);
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`saved ${outputPath}`);
