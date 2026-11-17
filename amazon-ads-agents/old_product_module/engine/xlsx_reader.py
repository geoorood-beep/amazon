"""Minimal stdlib reader for .xlsx / .csv / .tsv -> list of dict rows.

No third-party dependency, so it runs on a plain Python install (and on Grok's
cloud computer if it can run Python).
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def read_table(path: Path) -> list[dict[str, object]]:
    suffix = path.suffix.lower()
    if suffix in (".csv", ".tsv", ".txt"):
        return _read_delimited(path, "\t" if suffix == ".tsv" else None)
    if suffix in (".xlsx", ".xlsm"):
        return _rows_to_dicts(_read_xlsx_rows(path))
    raise ValueError(f"不支持的文件类型：{path.name}（只支持 .xlsx / .csv / .tsv）")


def _read_delimited(path: Path, delimiter: str | None) -> list[dict[str, object]]:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"无法识别编码：{path.name}")
    if delimiter is None:
        first = text.splitlines()[0] if text else ""
        delimiter = "\t" if first.count("\t") > first.count(",") else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    return _rows_to_dicts(rows)


def _rows_to_dicts(rows: list[list[object]]) -> list[dict[str, object]]:
    # Skip leading blank / title rows: header = first row with >= 3 non-empty cells.
    start = 0
    for i, row in enumerate(rows):
        if sum(1 for c in row if str(c).strip()) >= 3:
            start = i
            break
    if not rows:
        return []
    header = [str(h).strip() for h in rows[start]]
    out = []
    for row in rows[start + 1:]:
        if not any(str(c).strip() for c in row):
            continue
        out.append({header[i]: (row[i] if i < len(row) else "") for i in range(len(header)) if header[i]})
    return out


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _read_xlsx_rows(path: Path) -> list[list[object]]:
    with zipfile.ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", _NS):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t")))
        sheet_path = _first_sheet_path(zf)
        root = ET.fromstring(zf.read(sheet_path))
        rows: list[list[object]] = []
        for row in root.iter(f"{{{_NS['m']}}}row"):
            cells: dict[int, object] = {}
            for c in row.findall("m:c", _NS):
                idx = _col_index(c.get("r", "A1"))
                t = c.get("t")
                v = c.find("m:v", _NS)
                if t == "s" and v is not None:
                    val: object = shared[int(v.text)]
                elif t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(f"{{{_NS['m']}}}t"))
                elif v is not None and v.text is not None:
                    txt = v.text
                    try:
                        num = float(txt)
                        val = int(num) if num.is_integer() and t != "str" else num
                    except ValueError:
                        val = txt
                else:
                    val = ""
                cells[idx] = val
            if cells:
                width = max(cells) + 1
                rows.append([cells.get(i, "") for i in range(width)])
        return rows


def _first_sheet_path(zf: zipfile.ZipFile) -> str:
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    first = wb.find("m:sheets/m:sheet", _NS)
    rid = first.get(f"{{{_REL_NS}}}id") if first is not None else None
    if rid and "xl/_rels/workbook.xml.rels" in zf.namelist():
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        for rel in rels:
            if rel.get("Id") == rid:
                target = rel.get("Target", "").lstrip("/")
                return target if target.startswith("xl/") else f"xl/{target}"
    return "xl/worksheets/sheet1.xml"
