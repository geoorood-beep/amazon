from __future__ import annotations

import csv
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path

import pytest

from tools.threshold_calibrator.approval import build_change_set
from tools.threshold_calibrator.calibrator import (
    REQUIRED_COLUMNS,
    build_candidate_package,
    load_config,
    read_samples,
    sha256_file,
    write_outputs,
)
from tools.threshold_calibrator.monitor import evaluate, mark_notified


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/threshold_calibration.json"


def _rows(
    clicks_by_day: list[int],
    orders_by_day: list[int],
    *,
    segment_id: str = "area-small-sp-target-growth",
    dq_status: str = "DQ_PASS",
    windows: int = 1,
) -> list[dict[str, str]]:
    start = date(2026, 1, 1)
    result = []
    for index, (clicks, orders) in enumerate(zip(clicks_by_day, orders_by_day)):
        result.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "category": "rug",
                "segment_id": segment_id,
                "rug_type": "area_rug",
                "size_profile": "area_small",
                "ad_product_type": "SP",
                "strategy_stage": "growth",
                "object_grain": "TARGET",
                "object_id": "T-001",
                "marketplace": "US",
                "currency": "USD",
                "impressions": str(clicks * 10),
                "clicks": str(clicks),
                "orders": str(orders),
                "spend": str(clicks * (0.65 + index * 0.01)),
                "sales": str(orders * (26 + index * 0.2)),
                "attribution_mature": "true",
                "dq_status": dq_status,
                "validation_window_id": f"W{index * windows // len(clicks_by_day) + 1}",
                "source_ref": f"fixture:{index + 1}",
            }
        )
    return result


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def _proof_rows(*, reverse_holdout: bool = False) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    start = date(2026, 1, 1)
    for object_index in range(30):
        for day in range(30):
            holdout = day >= 21
            if holdout and reverse_holdout:
                orders = 35 - object_index
                cpa = Decimal("16.65") + Decimal(object_index) * Decimal("0.15")
                acos = Decimal("0.2775") + Decimal(object_index) * Decimal("0.0025")
            else:
                orders = 6 + object_index
                cpa = Decimal("21") - Decimal(object_index) * Decimal("0.15")
                acos = Decimal("0.35") - Decimal(object_index) * Decimal("0.0025")
            spend = Decimal(orders) * cpa
            sales = spend / acos
            result.append(
                {
                    "date": (start + timedelta(days=day)).isoformat(),
                    "category": "rug",
                    "segment_id": "area-small-sp-sku-size-growth",
                    "rug_type": "area_rug",
                    "size_profile": "area_small",
                    "ad_product_type": "SP",
                    "strategy_stage": "growth",
                    "object_grain": "SKU_SIZE",
                    "object_id": f"SKU-{object_index:02d}",
                    "marketplace": "US",
                    "currency": "USD",
                    "impressions": "1000",
                    "clicks": "100",
                    "orders": str(orders),
                    "spend": format(spend, "f"),
                    "sales": format(sales, "f"),
                    "attribution_mature": "true",
                    "dq_status": "DQ_PASS",
                    "validation_window_id": f"W{day // 10 + 1}",
                    "source_ref": f"proof:{object_index}:{day}",
                }
            )
    return result


def _package(source: Path) -> dict:
    rows, evidence = read_samples(source)
    return build_candidate_package(rows, evidence, load_config(CONFIG))


def test_reference_candidate_at_exact_gate(tmp_path: Path) -> None:
    clicks = [143] * 12 + [142] * 2
    orders = [4] * 8 + [3] * 6
    _write_csv(tmp_path / "history.csv", _rows(clicks, orders))
    package = _package(tmp_path)
    segment = package["segments"][0]
    assert segment["eligibility_status"] == "REFERENCE_CANDIDATE"
    assert segment["sample"]["clicks"] == 2000
    assert segment["sample"]["orders"] == 50
    assert segment["sample"]["distinct_days"] == 14
    assert segment["historical_validation"]["holdout_days"] >= 4
    assert segment["historical_validation"]["proves_future_superiority"] is False


def test_high_confidence_requires_three_windows_and_dq_pass(tmp_path: Path) -> None:
    clicks = [167] * 20 + [166] * 10
    orders = [4] * 10 + [3] * 20
    _write_csv(tmp_path / "history.csv", _rows(clicks, orders, windows=3))
    segment = _package(tmp_path)["segments"][0]
    assert segment["eligibility_status"] == "HIGH_CONFIDENCE_CANDIDATE"
    assert segment["sample"]["clicks"] == 5000
    assert segment["sample"]["orders"] == 100
    assert segment["sample"]["validation_windows"] == 3


@pytest.mark.parametrize(
    ("clicks", "orders"),
    [
        ([143] * 13 + [140], [4] * 8 + [3] * 6),  # 1,999 clicks / 50 orders
        ([143] * 12 + [142] * 2, [4] * 7 + [3] * 7),  # 2,000 / 49
    ],
)
def test_below_reference_gate_does_not_notify(
    tmp_path: Path, clicks: list[int], orders: list[int]
) -> None:
    _write_csv(tmp_path / "history.csv", _rows(clicks, orders))
    package = _package(tmp_path)
    assert package["segments"][0]["eligibility_status"] == "INSUFFICIENT_DATA"
    assert package["eligible_segment_count"] == 0


def test_zero_order_risk_is_not_threshold_update_candidate(tmp_path: Path) -> None:
    clicks = [22] * 6 + [21] * 8
    _write_csv(tmp_path / "history.csv", _rows(clicks, [0] * 14))
    package = _package(tmp_path)
    assert package["segments"][0]["eligibility_status"] == "ZERO_ORDER_RISK_CANDIDATE"
    assert package["eligible_segment_count"] == 0
    assert package["risk_candidate_count"] == 1


def test_duplicate_daily_object_across_files_is_blocked(tmp_path: Path) -> None:
    rows = _rows([100], [3])
    _write_csv(tmp_path / "a.csv", rows)
    _write_csv(tmp_path / "b.csv", rows)
    with pytest.raises(ValueError, match="重复日粒度"):
        read_samples(tmp_path)


def test_non_rug_history_is_rejected(tmp_path: Path) -> None:
    rows = _rows([100], [3])
    rows[0]["category"] = "office_chair"
    _write_csv(tmp_path / "history.csv", rows)
    with pytest.raises(ValueError, match="只允许category=rug"):
        read_samples(tmp_path)


def test_dq_blocked_segment_cannot_be_candidate(tmp_path: Path) -> None:
    _write_csv(tmp_path / "history.csv", _rows([200] * 14, [5] * 14, dq_status="DQ_BLOCKED"))
    package = _package(tmp_path)
    assert package["segments"][0]["eligibility_status"] == "DQ_BLOCKED"
    assert package["eligible_segment_count"] == 0


def test_approval_creates_pending_regression_and_never_auto_applies(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _write_csv(source / "history.csv", _proof_rows())
    outputs = write_outputs(_package(source), tmp_path / "out")
    candidate = json.loads(outputs["candidate"].read_text(encoding="utf-8"))
    approval = {
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": sha256_file(outputs["candidate"]),
        "decision": "APPROVED",
        "reviewer": "human-reviewer",
        "reviewed_at": "2026-08-04T10:00:00+08:00",
        "approved_scope": "area_small / SP / TARGET / growth",
        "notes": "fixture",
    }
    approval_path = tmp_path / "approval.json"
    approval_path.write_text(json.dumps(approval), encoding="utf-8")
    change_set = build_change_set(outputs["candidate"], approval_path)
    assert change_set["status"] == "HUMAN_APPROVED_PENDING_REGRESSION"
    assert change_set["auto_apply"] is False


def test_approval_rejects_eligible_but_unproven_candidate(tmp_path: Path) -> None:
    source = tmp_path / "source"
    clicks = [143] * 12 + [142] * 2
    orders = [4] * 8 + [3] * 6
    _write_csv(source / "history.csv", _rows(clicks, orders))
    outputs = write_outputs(_package(source), tmp_path / "out")
    candidate = json.loads(outputs["candidate"].read_text(encoding="utf-8"))
    approval = {
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": sha256_file(outputs["candidate"]),
        "decision": "APPROVED",
        "reviewer": "human-reviewer",
        "reviewed_at": "2026-08-04T10:00:00+08:00",
        "approved_scope": "area_small / SP / TARGET / growth",
    }
    approval_path = tmp_path / "approval.json"
    approval_path.write_text(json.dumps(approval), encoding="utf-8")
    with pytest.raises(ValueError, match="没有历史留出验证更优"):
        build_change_set(outputs["candidate"], approval_path)


def test_monitor_notifies_once_per_candidate(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    state = tmp_path / "state.json"
    clicks = [143] * 12 + [142] * 2
    orders = [4] * 8 + [3] * 6
    _write_csv(source / "history.csv", _rows(clicks, orders))
    first = evaluate(source, output, state, CONFIG)
    assert first["monitor_status"] == "NEW_CANDIDATE"
    assert first["should_notify"] is True
    mark_notified(
        first["candidate_id"], state, output / "threshold_calibration_status.json"
    )
    second = evaluate(source, output, state, CONFIG)
    assert second["monitor_status"] == "ALREADY_NOTIFIED"
    assert second["should_notify"] is False


def test_candidate_package_proves_historical_holdout_improvement(tmp_path: Path) -> None:
    _write_csv(tmp_path / "history.csv", _proof_rows())
    package = _package(tmp_path)
    segment = package["segments"][0]
    assert segment["eligibility_status"] == "HIGH_CONFIDENCE_CANDIDATE"
    assert segment["proof_status"] == "HISTORICALLY_BETTER_CANDIDATE"
    assert package["historically_better_segment_count"] == 1
    assert set(segment["candidate_thresholds"]) == {"cvr", "cpa", "acos"}
    assert all(
        item["status"] == "BETTER"
        for item in segment["historical_better_proof"]["metric_results"].values()
    )
    assert segment["historical_better_proof"]["proves_future_superiority"] is False


def test_candidate_package_rejects_reversed_holdout_as_not_better(tmp_path: Path) -> None:
    _write_csv(tmp_path / "history.csv", _proof_rows(reverse_holdout=True))
    segment = _package(tmp_path)["segments"][0]
    assert segment["proof_status"] == "NOT_BETTER"
    assert all(
        item["status"] == "WORSE"
        for item in segment["historical_better_proof"]["metric_results"].values()
    )
