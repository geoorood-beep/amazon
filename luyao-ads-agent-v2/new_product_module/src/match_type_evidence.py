from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from openpyxl import load_workbook

from .reference_adapter import normalize_term


_RELEVANCE_HEADERS = {
    "asin": ("ASIN", "asin", "产品ASIN"),
    "search_term": ("搜索词", "search_term", "Search Term"),
    "level": ("相关性结论", "relevance_level", "相关度"),
    "score": ("相关性得分", "relevance_score"),
    "reason": ("判断依据", "relevance_reason", "原因"),
}

_SEARCH_VOLUME_HEADERS = {
    "search_term": ("搜索词", "search_term", "Search Term"),
    "root": ("规范词根", "canonical_root", "normalized_root"),
    "month": ("月份", "month", "data_month"),
    "volume": ("月搜索量", "monthly_search_volume", "search_volume"),
    "marketplace": ("站点", "marketplace", "Marketplace"),
}

_LEVEL_ALIASES = {
    "HIGH": {"high", "highly relevant", "高", "高度相关", "强相关"},
    "MEDIUM": {"medium", "moderately relevant", "中", "中度相关"},
    "LOW": {"low", "weakly relevant", "低", "低度相关", "弱相关"},
    "IRRELEVANT": {"irrelevant", "not relevant", "不相关", "无关"},
}


@dataclass
class MatchTypeEvidence:
    relevance_by_key: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    term_demand_by_key: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    root_demand_by_key: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    issues: list[dict[str, str]] = field(default_factory=list)


def load_match_type_evidence(
    relevance_source: str | Path | None,
    search_volume_source: str | Path | None,
) -> MatchTypeEvidence:
    """Load optional user-maintained evidence for Phrase/Broad routing.

    Missing sources are represented as explicit pending states.  ABA rank is
    intentionally not accepted as a substitute for monthly search volume.
    """

    evidence = MatchTypeEvidence()
    relevance_paths = _iter_data_paths(relevance_source)
    search_volume_paths = _iter_data_paths(search_volume_source)

    if not relevance_paths:
        evidence.issues.append(
            {
                "code": "RELEVANCE_SOURCE_PENDING",
                "message": "尚未提供新品ASIN级相关性表，Phrase/Broad匹配方式必须待数据补充。",
            }
        )
    else:
        evidence.relevance_by_key = _load_relevance(relevance_paths)

    if not search_volume_paths:
        evidence.issues.append(
            {
                "code": "SEARCH_VOLUME_SOURCE_PENDING",
                "message": "尚未提供按月搜索量与规范词根表，不得用ABA排名代替月搜索量。",
            }
        )
    else:
        term_metrics, root_metrics = _load_search_volume(search_volume_paths)
        evidence.term_demand_by_key = term_metrics
        evidence.root_demand_by_key = root_metrics
    return evidence


def enrich_keyword_evidence(
    rows: list[dict[str, Any]],
    *,
    asin: str | None,
    marketplace: str | None,
    evidence: MatchTypeEvidence,
) -> list[dict[str, Any]]:
    normalized_asin = str(asin or "").strip().upper()
    normalized_marketplace = str(marketplace or "US").strip().upper()
    enriched: list[dict[str, Any]] = []

    for source_row in rows:
        row = dict(source_row)
        term = normalize_term(row.get("search_term"))
        relevance = evidence.relevance_by_key.get((normalized_asin, term))
        if relevance is None:
            relevance = evidence.relevance_by_key.get(("*", term))

        if relevance is None:
            row.update(
                {
                    "relevance_evidence_status": "PENDING_SOURCE",
                    "relevance_level": None,
                    "relevance_score": None,
                    "relevance_reason": None,
                    "relevance_source_files": [],
                }
            )
        else:
            row.update(
                {
                    "relevance_evidence_status": relevance["status"],
                    "relevance_level": relevance.get("level"),
                    "relevance_score": relevance.get("score"),
                    "relevance_reason": relevance.get("reason"),
                    "relevance_source_files": relevance.get("sources", []),
                }
            )

        root = normalize_term(row.get("normalized_root"))
        term_demand = evidence.term_demand_by_key.get((normalized_marketplace, term))
        if not root and term_demand:
            root = term_demand["root"]
            row["normalized_root"] = root
        root_demand = evidence.root_demand_by_key.get((normalized_marketplace, root)) if root else None

        row.update(
            {
                "monthly_search_volume": term_demand.get("monthly_search_volume") if term_demand else None,
                "root_monthly_search_volume": root_demand.get("root_monthly_search_volume") if root_demand else None,
                "root_top3_volume_share": root_demand.get("root_top3_volume_share") if root_demand else None,
                "root_distinct_query_count": root_demand.get("root_distinct_query_count") if root_demand else None,
                "search_volume_months": root_demand.get("months", []) if root_demand else [],
                "search_volume_source_files": root_demand.get("sources", []) if root_demand else [],
            }
        )

        readiness: list[str] = []
        if row["relevance_evidence_status"] != "READY":
            readiness.append("RELEVANCE_PENDING")
        if root_demand is None:
            readiness.append("ROOT_SEARCH_VOLUME_PENDING")
        row["match_type_evidence_status"] = "READY" if not readiness else "+".join(readiness)
        enriched.append(row)
    return enriched


def _iter_data_paths(source: str | Path | None) -> list[Path]:
    if source is None:
        return []
    path = Path(source)
    if path.is_dir():
        return sorted(
            item
            for item in path.iterdir()
            if item.is_file()
            and item.suffix.lower() in {".csv", ".xlsx", ".xlsm"}
            and not item.name.startswith(("~$", "."))
            and ".example." not in item.name.lower()
        )
    if path.is_file() and path.suffix.lower() in {".csv", ".xlsx", ".xlsm"}:
        return [path]
    return []


def _load_relevance(paths: list[Path]) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for path in paths:
        rows = _read_records(path)
        headers = set(rows[0]) if rows else set()
        required = ("asin", "search_term", "level")
        mapping = _resolve_headers(headers, _RELEVANCE_HEADERS, required, path)
        for row_number, row in enumerate(rows, start=2):
            asin = str(row.get(mapping["asin"]) or "").strip().upper()
            term = normalize_term(row.get(mapping["search_term"]))
            if not asin or not term:
                continue
            level = _normalize_relevance_level(row.get(mapping["level"]), path, row_number)
            score = _optional_float(row.get(mapping.get("score"))) if mapping.get("score") else None
            if score is not None and not 0 <= score <= 100:
                raise ValueError(f"{path.name} row {row_number} 相关性得分必须在0-100之间")
            reason = _text(row.get(mapping.get("reason"))) if mapping.get("reason") else None
            grouped.setdefault((asin, term), []).append(
                {"level": level, "score": score, "reason": reason, "source": path.name}
            )

    resolved: dict[tuple[str, str], dict[str, Any]] = {}
    for key, values in grouped.items():
        levels = {item["level"] for item in values}
        if len(levels) != 1:
            resolved[key] = {
                "status": "CONFLICT",
                "level": None,
                "score": None,
                "reason": "同一ASIN和搜索词存在相关性冲突",
                "sources": _unique(item["source"] for item in values),
            }
            continue
        scores = [item["score"] for item in values if item["score"] is not None]
        reasons = _unique(item["reason"] for item in values)
        resolved[key] = {
            "status": "READY",
            "level": next(iter(levels)),
            "score": median(scores) if scores else None,
            "reason": "；".join(reasons) if reasons else None,
            "sources": _unique(item["source"] for item in values),
        }
    return resolved


def _load_search_volume(
    paths: list[Path],
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    raw: dict[tuple[str, str, str], dict[str, Any]] = {}
    for path in paths:
        rows = _read_records(path)
        headers = set(rows[0]) if rows else set()
        required = ("search_term", "root", "month", "volume")
        mapping = _resolve_headers(headers, _SEARCH_VOLUME_HEADERS, required, path)
        for row_number, row in enumerate(rows, start=2):
            term = normalize_term(row.get(mapping["search_term"]))
            root = normalize_term(row.get(mapping["root"]))
            month = str(row.get(mapping["month"]) or "").strip()
            marketplace = (
                str(row.get(mapping.get("marketplace")) or "US").strip().upper()
                if mapping.get("marketplace")
                else "US"
            )
            if not term and not root and not month:
                continue
            if not term or not root or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
                raise ValueError(f"{path.name} row {row_number} 搜索词/规范词根/月份无效")
            volume = _required_nonnegative_integer(row.get(mapping["volume"]), path, row_number)
            key = (marketplace, month, term)
            existing = raw.get(key)
            if existing and (existing["root"] != root or existing["volume"] != volume):
                raise ValueError(
                    f"{path.name} row {row_number} 与已读取数据冲突："
                    f"{marketplace}/{month}/{term}"
                )
            if existing:
                existing["sources"] = _unique([*existing["sources"], path.name])
            else:
                raw[key] = {"root": root, "volume": volume, "sources": [path.name]}

    roots_by_term: dict[tuple[str, str], set[str]] = {}
    root_month_rows: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = {}
    for (marketplace, month, term), item in raw.items():
        roots_by_term.setdefault((marketplace, term), set()).add(item["root"])
        root_month_rows.setdefault((marketplace, item["root"], month), {})[term] = item
    conflicts = [key for key, roots in roots_by_term.items() if len(roots) > 1]
    if conflicts:
        sample = ", ".join(f"{market}/{term}" for market, term in conflicts[:5])
        raise ValueError(f"搜索词跨月份映射到多个规范词根：{sample}")

    root_metrics: dict[tuple[str, str], dict[str, Any]] = {}
    for marketplace, root in sorted({(key[0], key[1]) for key in root_month_rows}):
        months = sorted(
            month for market, candidate_root, month in root_month_rows if market == marketplace and candidate_root == root
        )[-3:]
        totals: list[float] = []
        shares: list[float] = []
        counts: list[int] = []
        sources: list[str] = []
        for month in months:
            items = list(root_month_rows[(marketplace, root, month)].values())
            total = sum(item["volume"] for item in items)
            if total <= 0:
                raise ValueError(f"{marketplace}/{root}/{month} 词根月搜索量合计必须大于0")
            totals.append(total)
            shares.append(sum(sorted((item["volume"] for item in items), reverse=True)[:3]) / total)
            counts.append(len(items))
            sources.extend(source for item in items for source in item["sources"])
        root_metrics[(marketplace, root)] = {
            "root_monthly_search_volume": median(totals),
            "root_top3_volume_share": median(shares),
            "root_distinct_query_count": int(median(counts)),
            "months": months,
            "sources": _unique(sources),
        }

    term_metrics: dict[tuple[str, str], dict[str, Any]] = {}
    for (marketplace, term), roots in roots_by_term.items():
        root = next(iter(roots))
        root_months = root_metrics[(marketplace, root)]["months"]
        values = [
            raw[(marketplace, month, term)]["volume"]
            for month in root_months
            if (marketplace, month, term) in raw
        ]
        sources = [
            source
            for month in root_months
            if (marketplace, month, term) in raw
            for source in raw[(marketplace, month, term)]["sources"]
        ]
        term_metrics[(marketplace, term)] = {
            "root": root,
            "monthly_search_volume": median(values),
            "months": root_months,
            "sources": _unique(sources),
        }
    return term_metrics, root_metrics


def _read_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    workbook = load_workbook(path, read_only=True, data_only=True)
    for sheet in workbook.worksheets:
        rows = sheet.iter_rows(values_only=True)
        header_values = next(rows, None)
        if not header_values:
            continue
        headers = [str(value or "").strip() for value in header_values]
        records = []
        for values in rows:
            if not any(value is not None and str(value).strip() for value in values):
                continue
            records.append(
                {headers[index]: values[index] if index < len(values) else None for index in range(len(headers))}
            )
        if records:
            return records
    return []


def _resolve_headers(
    headers: set[str],
    aliases: dict[str, tuple[str, ...]],
    required: tuple[str, ...],
    path: Path,
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for canonical, candidates in aliases.items():
        match = next((candidate for candidate in candidates if candidate in headers), None)
        if match:
            resolved[canonical] = match
    missing = [item for item in required if item not in resolved]
    if missing:
        raise ValueError(f"{path.name} 缺少字段：{missing}")
    return resolved


def _normalize_relevance_level(value: Any, path: Path, row_number: int) -> str:
    normalized = str(value or "").strip().lower()
    for canonical, aliases in _LEVEL_ALIASES.items():
        if normalized in aliases or normalized == canonical.lower():
            return canonical
    raise ValueError(f"{path.name} row {row_number} 相关性结论无效：{value}")


def _required_nonnegative_integer(value: Any, path: Path, row_number: int) -> int:
    try:
        parsed = float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path.name} row {row_number} 月搜索量无效：{value}") from exc
    if parsed < 0 or not parsed.is_integer():
        raise ValueError(f"{path.name} row {row_number} 月搜索量必须是非负整数")
    return int(parsed)


def _optional_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(str(value).strip().replace(",", ""))


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _unique(values: Iterable[Any]) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in values if value is not None and str(value).strip()))
