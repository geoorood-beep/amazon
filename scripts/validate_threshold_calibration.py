#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> int:
    print(f"THRESHOLD_CALIBRATION_INVALID: {message}")
    return 1


def main() -> int:
    required = [
        "thresholds/rug/calibration-eligibility.md",
        "contracts/threshold-calibration.md",
        "config/threshold_calibration.json",
        "config/threshold_calibration_samples.example.csv",
        "config/threshold_candidate_approval.example.json",
        "tools/threshold_calibrator/calibrator.py",
        "tools/threshold_calibrator/approval.py",
        "tools/threshold_calibrator/monitor.py",
        "tools/threshold_calibrator/proof.py",
        "scripts/check_threshold_calibration.py",
        "scripts/approve_threshold_candidate.py",
        "scripts/monitor_threshold_candidates.py",
    ]
    missing = [relative for relative in required if not (ROOT / relative).is_file()]
    if missing:
        return fail("缺少文件: " + ", ".join(missing))
    config = json.loads(
        (ROOT / "config/threshold_calibration.json").read_text(encoding="utf-8")
    )
    expected = {
        "reference_candidate": {
            "threshold_id": "THR-CAL-001",
            "minimum_valid_clicks": 2000,
            "minimum_ad_orders": 50,
            "minimum_distinct_days": 14,
        },
        "high_confidence_candidate": {
            "threshold_id": "THR-CAL-002",
            "minimum_valid_clicks": 5000,
            "minimum_ad_orders": 100,
            "minimum_distinct_days": 30,
            "minimum_validation_windows": 3,
        },
        "zero_order_risk_candidate": {
            "threshold_id": "THR-CAL-003",
            "minimum_valid_clicks": 300,
            "required_ad_orders": 0,
            "minimum_distinct_days": 14,
        },
    }
    for section, fields in expected.items():
        actual = config.get(section, {})
        for field, value in fields.items():
            if actual.get(field) != value:
                return fail(f"{section}.{field} 应为 {value!r}")
    if config.get("status") != "TEST_ONLY" or config.get("category") != "rug":
        return fail("配置必须保持 TEST_ONLY 且 category=rug")
    generation = config.get("candidate_generation", {})
    if generation.get("auto_apply") is not False:
        return fail("auto_apply必须为false")
    if generation.get("human_approval_required") is not True:
        return fail("human_approval_required必须为true")
    validation = generation.get("historical_validation", {})
    if validation.get("method") != "CHRONOLOGICAL_TRAIN_HOLDOUT":
        return fail("历史验证必须使用按时间训练/留出切分")
    proof = config.get("historical_better_proof", {})
    expected_proof = {
        "status": "TEST_ONLY",
        "applicable_grain": "SKU_SIZE",
        "current_threshold_source": "thresholds/rug/performance.md",
        "current_threshold_source_sha256": "a8475815f9f3c6648f29fa7ad1250e8051279d6aa16b541028b386e0e081193a",
        "minimum_candidate_objects": 7,
        "minimum_evaluable_objects": 20,
        "minimum_comparable_pairs": 100,
        "minimum_train_clicks_per_object": 30,
        "minimum_holdout_clicks_per_object": 10,
        "minimum_train_orders_for_cpa": 2,
        "minimum_holdout_orders_for_cpa": 1,
        "minimum_concordance_improvement": 0.05,
        "bootstrap_iterations": 1000,
        "minimum_better_metrics": 2,
        "reject_if_any_metric_worse": True,
    }
    for field, value in expected_proof.items():
        if proof.get(field) != value:
            return fail(f"historical_better_proof.{field} 应为 {value!r}")
    expected_profiles = {
        "doormat": {
            "cvr": ("higher_is_better", 0.075, 0.05, 0.035),
            "cpa": ("lower_is_better", 10, 13, 18),
            "acos": ("lower_is_better", 0.30, 0.55, 0.75),
        },
        "runner": {
            "cvr": ("higher_is_better", 0.08, 0.055, 0.035),
            "cpa": ("lower_is_better", 9, 13, 20),
            "acos": ("lower_is_better", 0.25, 0.45, 0.65),
        },
        "area_small": {
            "cvr": ("higher_is_better", 0.055, 0.035, 0.025),
            "cpa": ("lower_is_better", 15, 22, 35),
            "acos": ("lower_is_better", 0.25, 0.45, 0.65),
        },
        "area_large": {
            "cvr": ("higher_is_better", 0.05, 0.03, 0.02),
            "cpa": ("lower_is_better", 15, 24, 40),
            "acos": ("lower_is_better", 0.20, 0.35, 0.50),
        },
    }
    actual_profiles = proof.get("current_profiles", {})
    for profile, metrics in expected_profiles.items():
        for metric, expected in metrics.items():
            actual = actual_profiles.get(profile, {}).get(metric, {})
            current = (
                actual.get("direction"),
                actual.get("excellent"),
                actual.get("normal"),
                actual.get("warning"),
            )
            if current != expected:
                return fail(f"当前阈值派生配置不同步: {profile}.{metric}")
    canonical = (ROOT / "thresholds/rug/calibration-eligibility.md").read_text(
        encoding="utf-8"
    )
    for token in (
        "THR-CAL-001",
        "有效点击：`>= 2,000`",
        "广告订单：`>= 50`",
        "THR-CAL-002",
        "有效点击：`>= 5,000`",
        "广告订单：`>= 100`",
        "独立历史验证窗口：`>= 3`",
        "THR-CAL-003",
        "有效点击：`>= 300`",
        "广告订单：`= 0`",
        "HUMAN_APPROVED_PENDING_REGRESSION",
        "THR-CAL-004",
        "至少 `20` 个",
        "至少 `100` 对",
        "Bootstrap `1,000` 次",
        "`>=5` 个百分点",
    ):
        if token not in canonical:
            return fail(f"人工阈值正文缺少: {token}")
    agents = (ROOT / "agents/agents-directory.md").read_text(encoding="utf-8")
    for relative in (
        "thresholds/rug/calibration-eligibility.md",
        "contracts/threshold-calibration.md",
        "scripts/monitor_threshold_candidates.py",
    ):
        if relative not in agents:
            return fail(f"AGENTS目录缺少直达入口: {relative}")
    print(
        "THRESHOLD_CALIBRATION_VALID: candidate generation, holdout proof, "
        "human approval gate and monitor verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
