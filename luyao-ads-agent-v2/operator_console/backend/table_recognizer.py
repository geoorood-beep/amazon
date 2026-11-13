from __future__ import annotations

import csv
from datetime import date, datetime
import json
from pathlib import Path
import re
from typing import Any, Iterable, Iterator

from openpyxl import load_workbook


SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm", ".csv", ".tsv"}
ASIN_PATTERN = re.compile(r"\bB0[A-Z0-9]{8}\b", re.IGNORECASE)
HEADER_SCAN_ROWS = 20
DATA_SCAN_LIMIT = 250_000

FIELD_ALIASES: dict[str, set[str]] = {
    "asin": {"asin", "广告asin", "商品asin", "advertisedasin", "advertisedasin编号"},
    "sku": {"sku", "卖家sku", "广告sku", "advertisedsku"},
    "marketplace": {"站点", "市场", "marketplace", "market"},
    "size_spec": {"尺寸", "地毯尺寸", "规格", "size", "sizespec", "rugsize"},
    "rug_type": {"类型", "地毯类型", "品类", "rugtype", "producttype"},
    "style": {"风格", "style", "designstyle"},
    "color": {"颜色", "色系", "color", "colour"},
    "material": {"材质", "材料", "material", "fabric"},
    "scene_tags": {"场景", "使用场景", "场景标签", "适用场景", "scenetags", "room", "regiontags"},
    "order_target_daily": {"日订单目标", "目标日订单", "dailyordertarget", "ordertargetdaily"},
    "target_cpa": {"目标cpa", "targetcpa"},
    "daily_budget": {"日预算", "期望日预算", "dailybudget", "budget"},
}

DATE_ALIASES = {
    "日期", "date", "开始日期", "结束日期", "数据开始日", "数据结束日",
    "startdate", "enddate", "periodstart", "periodend",
}

VALUE_ALIASES: dict[str, dict[str, str]] = {
    "rug_type": {
        "arearug": "area_rug", "arearugs": "area_rug", "区域地毯": "area_rug",
        "runner": "runner", "runnerrug": "runner", "长条": "runner", "长条地毯": "runner",
        "doormat": "doormat", "门垫": "doormat",
        "round": "round", "roundrug": "round", "圆形": "round", "圆形地毯": "round",
    },
    "style": {"bohemian": "boho", "波西米亚": "boho", "复古": "vintage", "现代": "modern", "传统": "traditional", "农舍": "farmhouse"},
    "color": {"grey": "gray", "灰色": "gray", "蓝色": "blue", "红色": "red", "绿色": "green", "黑色": "black", "白色": "white", "粉色": "pink", "棕色": "brown"},
    "material": {"羊毛": "wool", "棉": "cotton", "棉质": "cotton", "黄麻": "jute", "聚酯纤维": "polyester", "聚酯": "polyester", "聚丙烯": "polypropylene"},
    "scene_tags": {"客厅": "living room", "卧室": "bedroom", "走廊": "hallway", "玄关": "entryway", "厨房": "kitchen"},
}


def normalize_header(value: Any) -> str:
    return re.sub(r"[\s_\-—–/\\:：()（）\[\]【】.]+", "", str(value or "").strip().casefold())


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean_value(value)
    if not text:
        return None
    for pattern in (
        r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})",
        r"(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})",
    ):
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            if pattern.startswith("(20"):
                year, month, day = map(int, match.groups())
            else:
                month, day, year = map(int, match.groups())
            return date(year, month, day)
        except ValueError:
            return None
    return None


def _csv_rows(path: Path) -> Iterator[list[Any]]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            handle = path.open("r", encoding=encoding, newline="")
            sample = handle.read(8192)
            handle.seek(0)
            delimiter = "\t" if path.suffix.casefold() == ".tsv" else None
            if delimiter is None:
                try:
                    delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
                except csv.Error:
                    delimiter = ","
            reader = csv.reader(handle, delimiter=delimiter)
            try:
                for row in reader:
                    yield row
            finally:
                handle.close()
            return
        except UnicodeError as exc:
            last_error = exc
    if last_error:
        raise last_error


def iter_tables(path: Path) -> Iterator[tuple[str, Iterable[list[Any]]]]:
    suffix = path.suffix.casefold()
    if suffix in {".xlsx", ".xlsm"}:
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            for worksheet in workbook.worksheets:
                # Amazon/WPS exports sometimes declare A1 as the worksheet
                # dimension even when the XML contains many thousands of rows.
                worksheet.reset_dimensions()
                yield worksheet.title, worksheet.iter_rows(values_only=True)
        finally:
            workbook.close()
        return
    if suffix in {".csv", ".tsv"}:
        yield path.stem, _csv_rows(path)
        return
    raise ValueError(f"不支持的表格格式: {path.suffix}")


def _field_for_header(header: Any) -> str | None:
    normalized = normalize_header(header)
    for field, aliases in FIELD_ALIASES.items():
        if normalized in aliases:
            return field
    return None


def _header_score(row: list[Any]) -> int:
    recognized = {_field_for_header(value) for value in row}
    date_count = sum(normalize_header(value) in DATE_ALIASES for value in row)
    return len(recognized - {None}) * 3 + date_count * 2


def find_header(rows: Iterator[list[Any]]) -> tuple[list[Any], list[list[Any]]]:
    preview: list[list[Any]] = []
    for _, row in zip(range(HEADER_SCAN_ROWS), rows):
        preview.append(list(row))
    if not preview:
        return [], []
    scored = [(_header_score(row), index) for index, row in enumerate(preview)]
    _, index = max(scored, key=lambda item: (item[0], -item[1]))
    return preview[index], preview[index + 1 :]


def _allowed_values(catalog: dict[str, Any], field: str) -> set[str]:
    return {str(item["value"]) for item in catalog.get("fields", {}).get(field, [])}


def normalize_catalog_value(field: str, value: Any, catalog: dict[str, Any]) -> str | None:
    text = clean_value(value)
    if not text:
        return None
    if field == "size_spec":
        text = re.sub(r"\s*(?:×|X|\*)\s*", "x", text.casefold())
        text = re.sub(r"\s*(?:ft|feet|foot|英尺)\s*", "", text)
        text = re.sub(r"[′'’\"]", "", text)
    key = normalize_header(text)
    normalized = VALUE_ALIASES.get(field, {}).get(key, text.casefold())
    return normalized if normalized in _allowed_values(catalog, field) else None


def normalize_scene_tags(value: Any, catalog: dict[str, Any]) -> list[str]:
    parts = re.split(r"[,，;；|/\n]+", clean_value(value))
    result: list[str] = []
    for part in parts:
        normalized = normalize_catalog_value("scene_tags", part, catalog)
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def recognize_new_product(path: Path, catalog: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    for sheet_name, raw_rows in iter_tables(path):
        rows = iter(raw_rows)
        header, buffered = find_header(rows)
        mapping = {index: field for index, value in enumerate(header) if (field := _field_for_header(value))}
        if not mapping:
            continue
        products: list[dict[str, str]] = []
        seen_asins: set[str] = set()
        for row_number, row in enumerate(list(buffered) + [list(item) for _, item in zip(range(1000), rows)], start=2):
            if not any(clean_value(value) for value in row):
                continue
            recognized: dict[str, Any] = {}
            for index, field in mapping.items():
                raw = row[index] if index < len(row) else None
                if field in {"rug_type", "size_spec", "style", "color", "material"}:
                    value = normalize_catalog_value(field, raw, catalog)
                    if clean_value(raw) and value is None:
                        warnings.append(f"{field} 的值“{clean_value(raw)}”不在本地属性库中，未自动选中")
                elif field == "scene_tags":
                    value = ",".join(normalize_scene_tags(raw, catalog))
                    if clean_value(raw) and not value:
                        warnings.append(f"场景“{clean_value(raw)}”不在本地属性库中，未自动选中")
                else:
                    value = clean_value(raw)
                    if field in {"asin", "marketplace"}:
                        value = value.upper()
                if value not in (None, ""):
                    recognized[field] = value
            if recognized:
                asin = str(recognized.get("asin") or "").upper()
                if not ASIN_PATTERN.fullmatch(asin):
                    warnings.append(f"第{row_number}行缺少有效ASIN，未加入产品清单")
                    continue
                if asin in seen_asins:
                    warnings.append(f"第{row_number}行ASIN {asin}重复，已保留首次出现的记录")
                    continue
                seen_asins.add(asin)
                recognized["asin"] = asin
                recognized.setdefault("marketplace", "US")
                products.append({key: str(value) for key, value in recognized.items()})
        if products:
            return {
                "source_file": path.name,
                "sheet": sheet_name,
                "fields": products[0],
                "products": products,
                "warnings": list(dict.fromkeys(warnings)),
            }
    return {
        "source_file": path.name,
        "sheet": None,
        "fields": {},
        "products": [],
        "warnings": ["没有找到可识别的新品字段表头或有效ASIN"],
    }


def scan_report_file(path: Path) -> dict[str, Any]:
    asins: set[str] = set()
    dates: list[date] = []
    sheets: list[str] = []
    row_count = 0
    for sheet_name, raw_rows in iter_tables(path):
        sheets.append(sheet_name)
        rows = iter(raw_rows)
        header, buffered = find_header(rows)
        normalized_headers = [normalize_header(value) for value in header]
        asin_indexes = [index for index, value in enumerate(normalized_headers) if value in FIELD_ALIASES["asin"]]
        date_indexes = [index for index, value in enumerate(normalized_headers) if value in DATE_ALIASES]
        remaining = DATA_SCAN_LIMIT - row_count
        if remaining <= 0:
            break
        data_rows = iter(buffered)
        for row in data_rows:
            row_count += 1
            for index in asin_indexes:
                if index < len(row):
                    asins.update(match.upper() for match in ASIN_PATTERN.findall(clean_value(row[index])))
            for index in date_indexes:
                if index < len(row) and (parsed := parse_date(row[index])):
                    dates.append(parsed)
            if row_count >= DATA_SCAN_LIMIT:
                break
        if row_count < DATA_SCAN_LIMIT:
            for row in rows:
                row_count += 1
                for index in asin_indexes:
                    if index < len(row):
                        asins.update(match.upper() for match in ASIN_PATTERN.findall(clean_value(row[index])))
                for index in date_indexes:
                    if index < len(row) and (parsed := parse_date(row[index])):
                        dates.append(parsed)
                if row_count >= DATA_SCAN_LIMIT:
                    break
    return {
        "name": path.name,
        "sheets": sheets,
        "rows_scanned": row_count,
        "asins": sorted(asins),
        "period_start": min(dates).isoformat() if dates else None,
        "period_end": max(dates).isoformat() if dates else None,
    }


def metadata_candidates(paths: list[Path]) -> list[Path]:
    """Choose the smallest source set that can identify advertised ASINs and dates."""
    daily_30 = [
        path for path in paths
        if "广告商品报告" in path.name and "每日明细" in path.name and "近30天" in path.name
    ]
    if daily_30:
        return daily_30[:1]
    summary_30 = [
        path for path in paths
        if "广告商品报告" in path.name and "汇总" in path.name and "近30天" in path.name
    ]
    if summary_30:
        return summary_30[:1]
    advertised_product = [
        path for path in paths
        if "广告商品报告" in path.name or "advertised" in path.name.casefold()
    ]
    return advertised_product or paths


def summarize_upload(upload_root: Path, catalog: dict[str, Any]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    report_asins: set[str] = set()
    dates: list[date] = []
    warnings: list[str] = []
    recognized_product: dict[str, Any] | None = None
    role_paths: dict[str, list[Path]] = {}
    entry_by_path: dict[Path, dict[str, Any]] = {}
    for role in ("new_product", "reports"):
        role_dir = upload_root / role
        paths = [
            path for path in sorted(role_dir.iterdir())
            if path.is_file() and path.suffix.casefold() in SUPPORTED_EXTENSIONS
        ] if role_dir.is_dir() else []
        role_paths[role] = paths
        for path in paths:
            entry = {"role": role, "name": path.name, "size": path.stat().st_size}
            files.append(entry)
            entry_by_path[path] = entry

    for path in role_paths["new_product"]:
        try:
            recognized_product = recognize_new_product(path, catalog)
            entry_by_path[path]["recognized_fields"] = sorted(recognized_product["fields"])
            warnings.extend(recognized_product["warnings"])
        except Exception as exc:
            entry_by_path[path]["error"] = str(exc)
            warnings.append(f"{path.name}: {exc}")

    scan_paths = metadata_candidates(role_paths["reports"])
    for path in scan_paths:
        try:
            scan = scan_report_file(path)
            entry_by_path[path].update({key: value for key, value in scan.items() if key != "name"})
            report_asins.update(scan["asins"])
            for key in ("period_start", "period_end"):
                if scan[key]:
                    dates.append(date.fromisoformat(scan[key]))
        except Exception as exc:
            entry_by_path[path]["error"] = str(exc)
            warnings.append(f"{path.name}: {exc}")
    detected_asins = sorted(report_asins)
    suggested_asins = sorted(report_asins)
    return {
        "upload_id": upload_root.name,
        "files": files,
        "detected_asins": detected_asins,
        "report_asins": sorted(report_asins),
        "suggested_asins": suggested_asins,
        "period_start": min(dates).isoformat() if dates else None,
        "period_end": max(dates).isoformat() if dates else None,
        "recognized_product": recognized_product,
        "paths": {
            "reports": str(upload_root / "reports") if (upload_root / "reports").is_dir() else None,
        },
        "warnings": warnings,
    }


def load_catalog(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
