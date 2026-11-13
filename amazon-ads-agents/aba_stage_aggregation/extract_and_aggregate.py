from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from openpyxl import load_workbook


SOP_PATH = Path("/Users/leo/Desktop/AI广告智能体项目SOP操作手册_V1.2_优化版.docx")
ABA_PATH = Path("/Users/leo/Desktop/26-6地毯ABA词库.xlsx")
OUT_PATH = Path("aba_stage_aggregation/data/aggregation.json")


PRODUCT_TYPES = [
    {
        "type": "圆形地毯 Round Rug",
        "aba_source": "跳过",
        "patterns": [r"\bround\b", r"\bcircle\b", r"\bcircular\b", r"\boval\b"],
    },
    {
        "type": "长条地毯 Runner Rug",
        "aba_source": "Runner Rug",
        "patterns": [
            r"\brunner\b",
            r"\bhallway\b",
            r"\bhall way\b",
            r"\bcorridor\b",
            r"\bstair runner\b",
            r"\b2\s*x\s*(5|6|7|8|10|12)\b",
            r"\b2\.5\s*x\s*(6|7|8|10|12)\b",
        ],
    },
    {
        "type": "门垫 Doormat",
        "aba_source": "Area Rug",
        "patterns": [
            r"\bdoor\s*mat\b",
            r"\bdoormat\b",
            r"\bentryway\b",
            r"\bfront door\b",
            r"\bwelcome mat\b",
            r"\bentrance\b",
            r"\boutdoor mat\b",
            r"\bdoorway\b",
            r"\bbath mat\b",
            r"\bbathroom mat\b",
        ],
    },
    {
        "type": "区域地毯 Area Rug",
        "aba_source": "Area Rug",
        "patterns": [
            r"\brug\b",
            r"\brugs\b",
            r"\bcarpet\b",
            r"\bmat\b",
            r"\bmats\b",
            r"\b2\s*x\s*3\b",
            r"\b3\s*x\s*5\b",
            r"\b5\s*x\s*(7|8)\b",
            r"\b6\s*x\s*9\b",
            r"\b7\s*x\s*9\b",
            r"\b8\s*x\s*10\b",
            r"\b9\s*x\s*12\b",
            r"\b10\s*x\s*14\b",
            r"\blarge\b",
            r"\bliving room\b",
            r"\bbedroom\b",
            r"\bdining room\b",
            r"\barea rug\b",
            r"\barea rugs\b",
        ],
    },
]


def iter_blocks(doc: Document):
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield "p", Paragraph(child, doc)
        elif isinstance(child, CT_Tbl):
            yield "t", Table(child, doc)


def table_rows(table: Table) -> list[list[str]]:
    return [[cell.text.strip().replace("\n", " / ") for cell in row.cells] for row in table.rows]


def parse_range(value: str) -> tuple[int, int]:
    text = value.replace(",", "").replace("＋", "+").replace(" ", "")
    m = re.search(r"(\d+)-(\d+)\+?", text)
    if not m:
        raise ValueError(f"Cannot parse ABA range: {value}")
    return int(m.group(1)), int(m.group(2))


def parse_percent(value: str) -> str:
    return value.replace("≥", "").replace("%", "").strip()


def extract_sop_rules() -> dict[str, Any]:
    doc = Document(SOP_PATH)
    stage_table = None
    old_rule_table = None
    for kind, block in iter_blocks(doc):
        if kind != "t":
            continue
        rows = table_rows(block)
        if rows and rows[0][:3] == ["订单阶段", "Area Rug 允许 ABA 排名区间", "Runner Rug 允许 ABA 排名区间"]:
            stage_table = rows
        if rows and rows[0][:3] == ["对象", "达到配置门槛后的判断", "动作"]:
            if any("ABA排名大于10W" in " ".join(row) for row in rows):
                old_rule_table = rows

    if stage_table is None:
        raise RuntimeError("SOP 4.3.2 stage table not found")

    stage_rules = []
    for row in stage_table[1:]:
        if not row or not row[0]:
            continue
        min_score = parse_percent(row[5])
        stage_rules.append(
            {
                "stage": row[0],
                "area_min": parse_range(row[1])[0],
                "area_max": parse_range(row[1])[1],
                "runner_min": parse_range(row[2])[0],
                "runner_max": parse_range(row[2])[1],
                "keyword_types": row[3],
                "examples": row[4],
                "min_match_score": min_score,
                "max_keyword_count": row[6],
            }
        )

    old_rule_text = ""
    if old_rule_table:
        for row in old_rule_table:
            if row and row[0] == "单词差、词根好":
                old_rule_text = " | ".join(row)
                break

    return {
        "stage_rules": stage_rules,
        "old_product_aba_rule": old_rule_text
        or "SOP 5.2.5: ABA排名大于10W就单独投，ABA排名小于10W就相关词合并投，或放进老广告组并增加预算。",
        "source_sop": str(SOP_PATH),
    }


def normalize_keyword(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def classify_product_types(keyword: str) -> list[dict[str, str]]:
    term = normalize_keyword(keyword)
    for product_type in PRODUCT_TYPES:
        if any(re.search(pattern, term) for pattern in product_type["patterns"]):
            return [
                {
                    "product_type": product_type["type"],
                    "aba_source": product_type["aba_source"],
                    "match_basis": "关键词文本命中：" + " / ".join(
                        pattern for pattern in product_type["patterns"] if re.search(pattern, term)
                    ),
                }
            ]
    return []


def load_table2_keywords() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    wb = load_workbook(ABA_PATH, read_only=True, data_only=True)
    sheet = wb.worksheets[1]
    header_months = [sheet.cell(2, col).value for col in range(1, sheet.max_column + 1)]
    rank_columns = []
    for col in range(2, sheet.max_column + 1):
        month = header_months[col - 1]
        if not month or month == "趋势图":
            break
        rank_columns.append((col, str(month)))
    rank_col, rank_month = rank_columns[-1]

    rows = []
    seen = set()
    for row in sheet.iter_rows(min_row=3, values_only=True):
        keyword = normalize_keyword(row[0])
        rank = row[rank_col - 1] if rank_col - 1 < len(row) else None
        if not keyword or rank in (None, ""):
            continue
        try:
            rank_int = int(float(rank))
        except (TypeError, ValueError):
            continue
        if keyword in seen:
            continue
        seen.add(keyword)
        rows.append({"keyword": keyword, "aba_rank": rank_int, "rank_month": rank_month})

    return rows, {
        "source_workbook": str(ABA_PATH),
        "source_sheet": sheet.title,
        "rank_month": rank_month,
        "rank_column_index": rank_col,
        "raw_keyword_rows": sheet.max_row - 2,
        "usable_keyword_rows": len(rows),
    }


def new_product_stage_matches(rank: int, aba_source: str, stage_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches = []
    if aba_source == "待配置":
        return matches
    for rule in stage_rules:
        if aba_source == "Runner Rug":
            low, high = rule["runner_min"], rule["runner_max"]
        else:
            low, high = rule["area_min"], rule["area_max"]
        if low <= rank <= high:
            matches.append(
                {
                    "stage": rule["stage"],
                    "aba_range": f"{low}-{high}",
                    "sop_keyword_types": rule["keyword_types"],
                    "min_match_score": rule["min_match_score"],
                    "max_keyword_count": rule["max_keyword_count"],
                }
            )
    return matches


def old_product_action(rank: int) -> str:
    if rank < 100000:
        return "老品：ABA<10W，相关词合并投，或放进老广告组并增加预算"
    if rank > 100000:
        return "老品：ABA>10W，单独投"
    return "老品：ABA=10W，SOP边界未明，待人工确认"


def main() -> None:
    rules = extract_sop_rules()
    keyword_rows, source = load_table2_keywords()
    new_detail = []
    old_detail = []
    skipped_round = []

    for row in keyword_rows:
        classifications = classify_product_types(row["keyword"])
        for item in classifications:
            if item["aba_source"] == "跳过":
                skipped_round.append({**row, **item, "reason": "按本次口径先跳过圆形地毯"})
                continue
            for match in new_product_stage_matches(row["aba_rank"], item["aba_source"], rules["stage_rules"]):
                new_detail.append({**row, **item, **match, "module": "模块一：新品推广"})
            old_detail.append(
                {
                    **row,
                    **item,
                    "module": "模块二：老品推广",
                    "old_product_action": old_product_action(row["aba_rank"]),
                    "aba_boundary": "10W",
                }
            )

    summary_counts = defaultdict(int)
    for row in new_detail:
        summary_counts[(row["module"], row["product_type"], row["stage"], row["aba_range"])] += 1

    summary = [
        {
            "module": module,
            "product_type": product_type,
            "stage": stage,
            "aba_range": aba_range,
            "keyword_count": count,
        }
        for (module, product_type, stage, aba_range), count in sorted(
            summary_counts.items(), key=lambda item: (item[0][0], item[0][1], item[0][2], item[0][3])
        )
    ]

    old_summary_counts = defaultdict(int)
    for row in old_detail:
        old_summary_counts[(row["product_type"], row["old_product_action"])] += 1
    old_summary = [
        {
            "module": "模块二：老品推广",
            "product_type": product_type,
            "stage_or_action": action,
            "keyword_count": count,
        }
        for (product_type, action), count in sorted(old_summary_counts.items())
    ]

    payload = {
        "source": source,
        "sop": rules,
        "source_keywords": sorted(keyword_rows, key=lambda r: (r["aba_rank"], r["keyword"])),
        "new_product_summary": summary,
        "new_product_detail": sorted(new_detail, key=lambda r: (r["product_type"], r["stage"], r["aba_rank"], r["keyword"])),
        "old_product_summary": old_summary,
        "old_product_detail": sorted(old_detail, key=lambda r: (r["product_type"], r["aba_rank"], r["keyword"])),
        "skipped_round": sorted(skipped_round, key=lambda r: (r["aba_rank"], r["keyword"])),
        "notes": [
            "表2按工作簿第二张工作表处理：月度变动2月。",
            "表2中ABA排名取第二行月份区块最右侧有效月份：2月。",
            "新品模块只按SOP 4.3.2 ABA阶段区间聚合；产品属性匹配和历史成交门槛仍需具体产品数据二次筛选。",
            "本版按用户确认的产品类型口径处理：门垫、长条、区域；圆形地毯先跳过不输出。",
            "SOP 4.3.2只提供Area Rug与Runner Rug区间；门垫、区域按Area Rug口径聚合，长条按Runner Rug口径聚合。",
            "老品模块只按SOP 5.2.5中ABA 10W结构动作聚合；实际放大仍需CPA/CVR/词根效果满足门槛。",
        ],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**source, "new_detail_rows": len(new_detail), "old_detail_rows": len(old_detail), "skipped_round_rows": len(skipped_round)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
