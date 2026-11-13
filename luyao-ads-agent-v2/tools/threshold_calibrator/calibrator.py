from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from math import sqrt
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .proof import build_historical_better_proof


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "threshold_calibration.json"
REQUIRED_COLUMNS = {
    "category",
    "date",
    "segment_id",
    "rug_type",
    "size_profile",
    "ad_product_type",
    "strategy_stage",
    "object_grain",
    "object_id",
    "marketplace",
    "currency",
    "impressions",
    "clicks",
    "orders",
    "spend",
    "sales",
    "attribution_mature",
    "dq_status",
    "validation_window_id",
    "source_ref",
}
ALLOWED_DQ = {"DQ_PASS", "DQ_WARNING", "DQ_BLOCKED"}
ELIGIBILITY_STATES = {
    "INSUFFICIENT_DATA",
    "ZERO_ORDER_RISK_CANDIDATE",
    "REFERENCE_CANDIDATE",
    "HIGH_CONFIDENCE_CANDIDATE",
    "DQ_BLOCKED",
}
METRIC_FIELDS = ("impressions", "clicks", "orders", "spend", "sales")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("status") != "TEST_ONLY":
        raise ValueError("阈值校准派生配置必须保持 TEST_ONLY")
    if config.get("category") != "rug":
        raise ValueError("阈值校准只允许 category=rug")
    if config.get("candidate_generation", {}).get("auto_apply") is not False:
        raise ValueError("候选阈值不得自动写入正式标准")
    if config.get("candidate_generation", {}).get("human_approval_required") is not True:
        raise ValueError("候选阈值必须要求人工批准")
    proof = config.get("historical_better_proof", {})
    if proof.get("status") != "TEST_ONLY":
        raise ValueError("历史更优证明必须保持TEST_ONLY")
    if proof.get("applicable_grain") != "SKU_SIZE":
        raise ValueError("历史更优证明必须与当前性能阈值粒度SKU_SIZE一致")
    if proof.get("current_threshold_source") != "thresholds/rug/performance.md":
        raise ValueError("当前性能阈值来源必须指向thresholds/rug/performance.md")
    current_threshold_path = ROOT / proof["current_threshold_source"]
    if proof.get("current_threshold_source_sha256") != sha256_file(
        current_threshold_path
    ):
        raise ValueError("当前性能阈值文件SHA-256与校准配置不一致")
    if int(proof.get("minimum_better_metrics", 0)) < 2:
        raise ValueError("历史更优证明至少要求两个指标BETTER")
    if proof.get("reject_if_any_metric_worse") is not True:
        raise ValueError("历史更优证明必须拒绝任一指标WORSE")
    return config


def _decimal(value: str, field: str) -> Decimal:
    text = str(value).strip().replace(",", "")
    if not text:
        raise ValueError(f"{field}为空")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{field}不是有效数字: {value}") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field}必须是非负有限数")
    return result


def _integer(value: str, field: str) -> int:
    parsed = _decimal(value, field)
    if parsed != parsed.to_integral_value():
        raise ValueError(f"{field}必须是整数")
    return int(parsed)


def _boolean(value: str, field: str) -> bool:
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"{field}必须是true/false")


def _date(value: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"date不是YYYY-MM-DD: {value}") from exc


def _normalize_row(raw: dict[str, str], source_path: Path, row_number: int) -> dict[str, Any]:
    missing = [name for name in REQUIRED_COLUMNS if not str(raw.get(name, "")).strip()]
    if missing:
        raise ValueError(
            f"{source_path.name}:{row_number} 缺少字段值: {', '.join(sorted(missing))}"
        )
    dq_status = raw["dq_status"].strip().upper()
    if dq_status not in ALLOWED_DQ:
        raise ValueError(f"{source_path.name}:{row_number} DQ状态无效: {dq_status}")
    impressions = _integer(raw["impressions"], "impressions")
    clicks = _integer(raw["clicks"], "clicks")
    orders = _integer(raw["orders"], "orders")
    spend = _decimal(raw["spend"], "spend")
    sales = _decimal(raw["sales"], "sales")
    if clicks > impressions:
        raise ValueError(f"{source_path.name}:{row_number} clicks不能大于impressions")
    if orders > clicks:
        raise ValueError(f"{source_path.name}:{row_number} orders不能大于clicks")
    category = raw["category"].strip().casefold()
    if category != "rug":
        raise ValueError(f"{source_path.name}:{row_number} 只允许category=rug")
    ad_product_type = raw["ad_product_type"].strip().upper()
    if ad_product_type != "SP":
        raise ValueError(f"{source_path.name}:{row_number} 当前只支持SP")
    return {
        "category": category,
        "date": _date(raw["date"]),
        "segment_id": raw["segment_id"].strip(),
        "rug_type": raw["rug_type"].strip(),
        "size_profile": raw["size_profile"].strip(),
        "ad_product_type": ad_product_type,
        "strategy_stage": raw["strategy_stage"].strip(),
        "object_grain": raw["object_grain"].strip().upper(),
        "object_id": raw["object_id"].strip(),
        "marketplace": raw["marketplace"].strip().upper(),
        "currency": raw["currency"].strip().upper(),
        "impressions": impressions,
        "clicks": clicks,
        "orders": orders,
        "spend": spend,
        "sales": sales,
        "attribution_mature": _boolean(raw["attribution_mature"], "attribution_mature"),
        "dq_status": dq_status,
        "validation_window_id": raw["validation_window_id"].strip(),
        "source_ref": raw["source_ref"].strip(),
        "source_file": str(source_path),
        "source_row": row_number,
    }


def read_samples(source_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files = sorted(source_dir.glob("*.csv"))
    if not files:
        return [], []
    rows: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    seen: dict[tuple[str, date, str, str, str], dict[str, Any]] = {}
    for path in files:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = set(reader.fieldnames or [])
            missing_columns = sorted(REQUIRED_COLUMNS - headers)
            if missing_columns:
                raise ValueError(f"{path.name}缺少列: {', '.join(missing_columns)}")
            file_rows = 0
            for row_number, raw in enumerate(reader, start=2):
                if not any(str(value or "").strip() for value in raw.values()):
                    continue
                row = _normalize_row(raw, path, row_number)
                key = (
                    row["segment_id"],
                    row["date"],
                    row["object_grain"],
                    row["object_id"],
                    row["strategy_stage"],
                )
                if key in seen:
                    previous = seen[key]
                    raise ValueError(
                        "重复日粒度: "
                        f"{key}，来源={previous['source_file']}:{previous['source_row']} / "
                        f"{path}:{row_number}"
                    )
                seen[key] = row
                rows.append(row)
                file_rows += 1
            evidence.append(
                {
                    "file_name": path.name,
                    "source_path": str(path),
                    "sha256": sha256_file(path),
                    "row_count": file_rows,
                }
            )
    return rows, evidence


def _ratio(numerator: Decimal | int, denominator: Decimal | int) -> Decimal | None:
    denominator_decimal = Decimal(denominator)
    if denominator_decimal == 0:
        return None
    return Decimal(numerator) / denominator_decimal


def _quantile(values: Iterable[Decimal], q: Decimal) -> Decimal | None:
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = q * Decimal(len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - Decimal(lower)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[Decimal, Decimal] | None:
    if trials <= 0:
        return None
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    half = z * sqrt((p * (1 - p) / trials) + (z * z / (4 * trials * trials))) / denominator
    return Decimal(str(max(0.0, center - half))), Decimal(str(min(1.0, center + half)))


def _daily_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Decimal | date | None]]:
    grouped: dict[date, dict[str, Decimal | int]] = defaultdict(
        lambda: {
            "impressions": 0,
            "clicks": 0,
            "orders": 0,
            "spend": Decimal("0"),
            "sales": Decimal("0"),
        }
    )
    for row in rows:
        bucket = grouped[row["date"]]
        for field in ("impressions", "clicks", "orders"):
            bucket[field] = int(bucket[field]) + int(row[field])
        for field in ("spend", "sales"):
            bucket[field] = Decimal(bucket[field]) + Decimal(row[field])
    result: list[dict[str, Decimal | date | None]] = []
    for day, values in sorted(grouped.items()):
        result.append(
            {
                "date": day,
                "cvr": _ratio(values["orders"], values["clicks"]),
                "cpa": _ratio(values["spend"], values["orders"]),
                "acos": _ratio(values["spend"], values["sales"]),
            }
        )
    return result


def _candidate_boundaries(
    rows: list[dict[str, Any]], minimum_observations: int
) -> tuple[dict[str, Any], list[str]]:
    daily = _daily_metrics(rows)
    definitions = {
        "cvr": "higher_is_better",
        "cpa": "lower_is_better",
        "acos": "lower_is_better",
    }
    result: dict[str, Any] = {}
    issues: list[str] = []
    for metric, direction in definitions.items():
        values = [Decimal(item[metric]) for item in daily if item[metric] is not None]
        if len(values) < minimum_observations:
            issues.append(
                f"{metric.upper()}只有{len(values)}个有效日，少于{minimum_observations}，不生成四档边界"
            )
            continue
        p25 = _quantile(values, Decimal("0.25"))
        p50 = _quantile(values, Decimal("0.50"))
        p75 = _quantile(values, Decimal("0.75"))
        assert p25 is not None and p50 is not None and p75 is not None
        if len({p25, p50, p75}) < 3:
            issues.append(f"{metric.upper()}分布分位点重合，不生成四档边界")
            continue
        if direction == "higher_is_better":
            boundaries = {
                "excellent_lower": p75,
                "normal_lower": p50,
                "warning_lower": p25,
            }
        else:
            boundaries = {
                "excellent_upper": p25,
                "normal_upper": p50,
                "warning_upper": p75,
            }
        result[metric] = {
            "direction": direction,
            "daily_observation_count": len(values),
            "p25": p25,
            "p50": p50,
            "p75": p75,
            "provisional_boundaries": boundaries,
            "status": "HISTORICAL_DISTRIBUTION_CANDIDATE",
        }
    return result, issues


def _historical_validation(
    rows: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    """Time-split evidence; intentionally does not claim future superiority."""
    settings = config["candidate_generation"]["historical_validation"]
    days = sorted({row["date"] for row in rows})
    minimum_holdout_days = int(settings["minimum_holdout_days"])
    if len(days) < minimum_holdout_days + 1:
        return {
            "method": settings["method"],
            "evidence_status": "INSUFFICIENT_HOLDOUT_DAYS",
            "distinct_days": len(days),
            "minimum_holdout_days": minimum_holdout_days,
            "proves_future_superiority": False,
        }
    split_index = int(len(days) * Decimal(str(settings["train_fraction"])))
    split_index = max(1, min(split_index, len(days) - minimum_holdout_days))
    train_days = set(days[:split_index])
    holdout_days = set(days[split_index:])
    train_totals = _totals([row for row in rows if row["date"] in train_days])
    holdout_totals = _totals([row for row in rows if row["date"] in holdout_days])

    def metrics(totals: dict[str, Decimal | int]) -> dict[str, Decimal | None]:
        return {
            "cvr": _ratio(totals["orders"], totals["clicks"]),
            "cpa": _ratio(totals["spend"], totals["orders"]),
            "acos": _ratio(totals["spend"], totals["sales"]),
        }

    return {
        "method": settings["method"],
        "evidence_status": "HISTORICAL_HOLDOUT_EVIDENCE_ONLY",
        "train_period": {"start": min(train_days), "end": max(train_days)},
        "holdout_period": {"start": min(holdout_days), "end": max(holdout_days)},
        "train_days": len(train_days),
        "holdout_days": len(holdout_days),
        "train_sample": train_totals,
        "holdout_sample": holdout_totals,
        "train_metrics": metrics(train_totals),
        "holdout_metrics": metrics(holdout_totals),
        "proves_future_superiority": False,
        "interpretation": (
            "时间留出集只能检查历史稳定性；只有相对当前阈值的同目标回放、"
            "业务护栏和人工批准完成后，才可称为更优候选。"
        ),
    }


def _totals(rows: list[dict[str, Any]]) -> dict[str, Decimal | int]:
    return {
        "impressions": sum(int(row["impressions"]) for row in rows),
        "clicks": sum(int(row["clicks"]) for row in rows),
        "orders": sum(int(row["orders"]) for row in rows),
        "spend": sum((Decimal(row["spend"]) for row in rows), Decimal("0")),
        "sales": sum((Decimal(row["sales"]) for row in rows), Decimal("0")),
    }


def _shortfall(actual: int, required: int) -> int:
    return max(required - actual, 0)


def _segment_result(
    segment_id: str,
    rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    dimensions = {
        field: sorted({str(row[field]) for row in rows})
        for field in (
            "rug_type",
            "size_profile",
            "ad_product_type",
            "strategy_stage",
            "object_grain",
            "marketplace",
            "currency",
        )
    }
    mixed = [field for field, values in dimensions.items() if len(values) != 1]
    issues: list[str] = []
    if mixed:
        issues.append("Calibration Segment混入多个维度: " + ", ".join(mixed))
    if any(row["dq_status"] == "DQ_BLOCKED" for row in rows):
        issues.append("分组包含DQ_BLOCKED数据")
    immature = [row for row in rows if not row["attribution_mature"]]
    if immature:
        issues.append(f"分组包含{len(immature)}行未成熟归因数据")
    valid_rows = [
        row
        for row in rows
        if row["dq_status"] != "DQ_BLOCKED" and row["attribution_mature"]
    ]
    totals = _totals(valid_rows)
    distinct_days = len({row["date"] for row in valid_rows})
    windows = len({row["validation_window_id"] for row in valid_rows})
    dq_statuses = {row["dq_status"] for row in valid_rows}
    high = config["high_confidence_candidate"]
    reference = config["reference_candidate"]
    zero = config["zero_order_risk_candidate"]
    if mixed or any(row["dq_status"] == "DQ_BLOCKED" for row in rows):
        state = "DQ_BLOCKED"
        threshold_id = None
    elif (
        totals["clicks"] >= high["minimum_valid_clicks"]
        and totals["orders"] >= high["minimum_ad_orders"]
        and distinct_days >= high["minimum_distinct_days"]
        and windows >= high["minimum_validation_windows"]
        and dq_statuses <= set(high["allowed_dq_statuses"])
        and not immature
    ):
        state = "HIGH_CONFIDENCE_CANDIDATE"
        threshold_id = high["threshold_id"]
    elif (
        totals["clicks"] >= reference["minimum_valid_clicks"]
        and totals["orders"] >= reference["minimum_ad_orders"]
        and distinct_days >= reference["minimum_distinct_days"]
        and dq_statuses <= set(reference["allowed_dq_statuses"])
        and not immature
    ):
        state = "REFERENCE_CANDIDATE"
        threshold_id = reference["threshold_id"]
    elif (
        totals["clicks"] >= zero["minimum_valid_clicks"]
        and totals["orders"] == zero["required_ad_orders"]
        and distinct_days >= zero["minimum_distinct_days"]
        and dq_statuses <= set(zero["allowed_dq_statuses"])
        and not immature
    ):
        state = "ZERO_ORDER_RISK_CANDIDATE"
        threshold_id = zero["threshold_id"]
    else:
        state = "INSUFFICIENT_DATA"
        threshold_id = None
    assert state in ELIGIBILITY_STATES
    metrics = {
        "ctr": _ratio(totals["clicks"], totals["impressions"]),
        "cvr": _ratio(totals["orders"], totals["clicks"]),
        "cpc": _ratio(totals["spend"], totals["clicks"]),
        "cpa": _ratio(totals["spend"], totals["orders"]),
        "acos": _ratio(totals["spend"], totals["sales"]),
    }
    interval = _wilson_interval(int(totals["orders"]), int(totals["clicks"]))
    candidate_thresholds: dict[str, Any] = {}
    descriptive_daily_distribution: dict[str, Any] = {}
    historical_validation: dict[str, Any] | None = None
    historical_better_proof: dict[str, Any] | None = None
    if state in {"REFERENCE_CANDIDATE", "HIGH_CONFIDENCE_CANDIDATE"}:
        descriptive_daily_distribution, boundary_issues = _candidate_boundaries(
            valid_rows,
            config["candidate_generation"]["minimum_daily_metric_observations"],
        )
        issues.extend(boundary_issues)
        historical_validation = _historical_validation(valid_rows, config)
        if historical_validation["evidence_status"] == "HISTORICAL_HOLDOUT_EVIDENCE_ONLY":
            candidate_thresholds, historical_better_proof = build_historical_better_proof(
                valid_rows,
                dimensions["size_profile"][0],
                dimensions["object_grain"][0],
                config,
            )
    reference_shortfall = {
        "clicks": _shortfall(int(totals["clicks"]), reference["minimum_valid_clicks"]),
        "orders": _shortfall(int(totals["orders"]), reference["minimum_ad_orders"]),
        "distinct_days": _shortfall(distinct_days, reference["minimum_distinct_days"]),
    }
    return {
        "segment_id": segment_id,
        "dimensions": dimensions,
        "eligibility_status": state,
        "eligibility_threshold_id": threshold_id,
        "sample": {
            **totals,
            "distinct_days": distinct_days,
            "validation_windows": windows,
            "mature_row_count": len(valid_rows),
            "immature_row_count": len(immature),
        },
        "metrics": metrics,
        "cvr_95_wilson_interval": (
            {"lower": interval[0], "upper": interval[1]} if interval else None
        ),
        "reference_candidate_shortfall": reference_shortfall,
        "candidate_thresholds": candidate_thresholds,
        "descriptive_daily_distribution": descriptive_daily_distribution,
        "historical_validation": historical_validation,
        "historical_better_proof": historical_better_proof,
        "proof_status": (
            historical_better_proof["overall_status"]
            if historical_better_proof is not None
            else "NOT_ELIGIBLE_FOR_THRESHOLD_UPDATE"
        ),
        "issues": issues,
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def build_candidate_package(
    rows: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["segment_id"]].append(row)
    segments = [
        _segment_result(segment_id, grouped[segment_id], config)
        for segment_id in sorted(grouped)
    ]
    current_threshold_source = config["historical_better_proof"][
        "current_threshold_source"
    ]
    current_threshold_evidence = {
        "path": current_threshold_source,
        "sha256": sha256_file(ROOT / current_threshold_source),
    }
    material = json.dumps(
        {
            "config": config,
            "current_threshold_evidence": current_threshold_evidence,
            "evidence": [(item["file_name"], item["sha256"]) for item in evidence],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    candidate_id = "THRCAND-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    timezone_name = config.get("timezone", "Asia/Shanghai")
    return _json_ready(
        {
            "schema_version": "1.0",
            "package_type": "THRESHOLD_CALIBRATION_CANDIDATE",
            "candidate_id": candidate_id,
            "generated_at": datetime.now(ZoneInfo(timezone_name)),
            "config_version": config["config_version"],
            "maintenance_source": config["maintenance_source"],
            "category": "rug",
            "auto_apply": False,
            "human_approval_required": True,
            "eligible_segment_count": sum(
                item["eligibility_status"]
                in {"REFERENCE_CANDIDATE", "HIGH_CONFIDENCE_CANDIDATE"}
                for item in segments
            ),
            "risk_candidate_count": sum(
                item["eligibility_status"] == "ZERO_ORDER_RISK_CANDIDATE"
                for item in segments
            ),
            "historically_better_segment_count": sum(
                item["proof_status"] == "HISTORICALLY_BETTER_CANDIDATE"
                for item in segments
            ),
            "segments": segments,
            "evidence": evidence,
            "current_threshold_evidence": current_threshold_evidence,
        }
    )


def _fmt(value: Any, *, percent: bool = False) -> str:
    if value is None:
        return "—"
    number = Decimal(str(value))
    if percent:
        return f"{number * Decimal('100'):.2f}%"
    return f"{number:.2f}"


def render_markdown(package: dict[str, Any]) -> str:
    lines = [
        "# Rug 候选阈值包",
        "",
        f"- Candidate ID：`{package['candidate_id']}`",
        f"- 生成时间：`{package['generated_at']}`",
        f"- 达标分组：`{package['eligible_segment_count']}`",
        f"- 零订单风险分组：`{package['risk_candidate_count']}`",
        f"- 历史留出验证更优分组：`{package['historically_better_segment_count']}`",
        "- 自动应用：`false`",
        "- 人工批准：`required`",
        "",
        "| Segment | 资格状态 | 更优证据 | 点击 | 订单 | 日期 | CVR | CPA | ACOS | 距参考门点击 | 距参考门订单 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in package["segments"]:
        sample = item["sample"]
        shortfall = item["reference_candidate_shortfall"]
        metrics = item["metrics"]
        lines.append(
            "| "
            + " | ".join(
                [
                    item["segment_id"],
                    item["eligibility_status"],
                    item["proof_status"],
                    str(sample["clicks"]),
                    str(sample["orders"]),
                    str(sample["distinct_days"]),
                    _fmt(metrics["cvr"], percent=True),
                    _fmt(metrics["cpa"]),
                    _fmt(metrics["acos"], percent=True),
                    str(shortfall["clicks"]),
                    str(shortfall["orders"]),
                ]
            )
            + " |"
        )
    better_segments = [
        item
        for item in package["segments"]
        if item["proof_status"] == "HISTORICALLY_BETTER_CANDIDATE"
    ]
    if better_segments:
        lines.extend(["", "## 历史留出验证更优的候选边界", ""])
        for item in better_segments:
            lines.extend(
                [
                    f"### {item['segment_id']}",
                    "",
                    "| 指标 | 优质边界 | 正常边界 | 警戒边界 | 当前一致率 | 候选一致率 | 提升 |",
                    "|---|---:|---:|---:|---:|---:|---:|",
                ]
            )
            proof_metrics = item["historical_better_proof"]["metric_results"]
            for metric, thresholds in item["candidate_thresholds"].items():
                evidence = proof_metrics[metric]
                percent = metric in {"cvr", "acos"}
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            metric.upper(),
                            _fmt(thresholds["excellent"], percent=percent),
                            _fmt(thresholds["normal"], percent=percent),
                            _fmt(thresholds["warning"], percent=percent),
                            _fmt(evidence["current_holdout_concordance"], percent=True),
                            _fmt(evidence["candidate_holdout_concordance"], percent=True),
                            _fmt(evidence["concordance_improvement"], percent=True),
                        ]
                    )
                    + " |"
                )
    lines.extend(
        [
            "",
            "## 使用边界",
            "",
            "达标只允许生成候选阈值。人工批准后仍需回归、压力测试、来源登记和版本清单校验；本文件不得直接覆盖正式阈值。",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(package: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = output_dir / "threshold_candidate.json"
    markdown_path = output_dir / "threshold_candidate.md"
    status_path = output_dir / "threshold_calibration_status.json"
    notification_path = output_dir / "notification.md"
    candidate_path.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(package), encoding="utf-8")
    status = {
        "candidate_id": package["candidate_id"],
        "candidate_sha256": sha256_file(candidate_path),
        "eligible_segment_count": package["eligible_segment_count"],
        "risk_candidate_count": package["risk_candidate_count"],
        "historically_better_segment_count": package[
            "historically_better_segment_count"
        ],
        "should_notify": package["eligible_segment_count"] > 0,
        "auto_apply": False,
        "human_approval_required": True,
    }
    status_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if status["should_notify"]:
        notification_path.write_text(
            "阈值样本门已达标，请人工审核候选阈值包：\n\n"
            f"- Candidate ID：`{package['candidate_id']}`\n"
            f"- 达标分组：`{package['eligible_segment_count']}`\n"
            f"- 历史留出验证更优分组：`{package['historically_better_segment_count']}`\n"
            f"- 候选文件：`{candidate_path}`\n"
            "- 状态：`CANDIDATE_ONLY / HUMAN_APPROVAL_REQUIRED`\n",
            encoding="utf-8",
        )
    elif notification_path.exists():
        notification_path.unlink()
    return {
        "candidate": candidate_path,
        "markdown": markdown_path,
        "status": status_path,
        "notification": notification_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查Rug历史广告样本门并生成候选阈值包")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_dir = Path(args.source_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    config = load_config(Path(args.config).expanduser().resolve())
    rows, evidence = read_samples(source_dir)
    if not rows:
        print(f"NO_INPUT: {source_dir} 中没有阈值校准CSV")
        return 0
    package = build_candidate_package(rows, evidence, config)
    outputs = write_outputs(package, output_dir)
    print(f"Candidate ID: {package['candidate_id']}")
    print(f"Eligible segments: {package['eligible_segment_count']}")
    print(f"Risk candidates: {package['risk_candidate_count']}")
    print(f"Should notify: {package['eligible_segment_count'] > 0}")
    print(f"Candidate: {outputs['candidate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
