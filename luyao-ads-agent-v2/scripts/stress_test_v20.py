#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from openpyxl import Workbook
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_ads.arbitration import arbitrate_actions  # noqa: E402
from ai_ads.contracts import (  # noqa: E402
    ActionType,
    MetricWindow,
    ObjectType,
    RuleSourceStatus,
    RunMode,
    ValidationOutcome,
)
from ai_ads.data_quality import assess_data_quality  # noqa: E402
from ai_ads.tests.factories import NOW, action, context, package, packet, plan  # noqa: E402
from ai_ads.validator import _validate_action, validate_plan  # noqa: E402
from new_product_module.src.pipeline import run_new_product_pipeline  # noqa: E402
from new_product_module.src.reference_adapter import load_rug_keyword_evidence  # noqa: E402
from new_product_module.src.rule_loader import load_rules  # noqa: E402
from new_product_module.src.schemas import ProductInfo  # noqa: E402


def _codes(report) -> set[str]:
    return {item.code for item in report.findings}


def _validate(actions, *, source_packet=None, source_context=None, run_mode=RunMode.TEST_ONLY, active=False):
    source_packet = source_packet or packet()
    source_context = source_context or context()
    candidate, arbitration = plan(actions)
    current_package = package(
        rule_status=RuleSourceStatus.ACTIVE if active else RuleSourceStatus.PROVIDED_FOR_TEST,
        threshold_status=(
            RuleSourceStatus.ACTIVE if active else RuleSourceStatus.PROVIDED_FOR_TEST
        ),
    )
    return validate_plan(
        packet=source_packet,
        context=source_context,
        package=current_package,
        arbitration=arbitration,
        plan=candidate,
        run_mode=run_mode,
        now=NOW,
    )


def _write_aba(path: Path, rank: float) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "广告词库"
    sheet.append(["搜索词", "搜索量排名", "地毯类型", "推荐层级", "相关度等级", "合规状态", "广告状态"])
    sheet.append(["washable rug", rank, "area_rug", "P1", "高", "安全", "可投"])
    workbook.save(path)


def _write_history(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "term_summary"
    sheet.append(["search_term", "clicks", "ad_orders", "cvr", "cpa", "source_files"])
    sheet.append(["Washable  Rug", 100, 10, 0.10, 10, "first.xlsx"])
    sheet.append(["washable rug", 1, 0, 0, 99, "second.xlsx"])
    workbook.save(path)


def main() -> int:
    results: dict[str, object] = {}

    production_report = _validate(
        [action()],
        run_mode=RunMode.PRODUCTION,
        active=True,
    )
    assert production_report.outcome == ValidationOutcome.BLOCKED
    assert "PRODUCTION_EXECUTION_DISABLED" in _codes(production_report)
    results["production_fuse"] = "BLOCKED"

    empty = packet()
    empty.campaigns = []
    empty.ad_groups = []
    empty.targets = []
    empty.search_terms = []
    empty.metrics = []
    empty.report_sources = [
        item.model_copy(update={"row_count": 0}) for item in empty.report_sources
    ]
    empty_report = assess_data_quality(empty)
    assert empty_report.status.value == "DQ_BLOCKED"
    results["empty_full_packet"] = empty_report.status.value

    wrong_direction = action(
        action_type=ActionType.INCREASE_BUDGET,
        object_type=ObjectType.CAMPAIGN,
        object_id="C-001",
        current_value=Decimal("100"),
        proposed_value=Decimal("10"),
    )
    wrong_report = _validate([wrong_direction])
    assert wrong_report.outcome == ValidationOutcome.BLOCKED
    assert "ACTION_DIRECTION_INVALID" in _codes(wrong_report)
    results["wrong_direction_action"] = "BLOCKED"

    rng = random.Random(20260803)
    fuzz_count = 2_000
    base_packet = packet()
    base_context = context()
    fuzz_start = perf_counter()
    for index in range(fuzz_count):
        current = Decimal(str(rng.randint(1, 10_000))) / Decimal("100")
        proposed = current - Decimal(str(rng.randint(0, 100))) / Decimal("100")
        invalid = action(
            action_id=f"FUZZ-{index:05d}",
            current_value=current,
            proposed_value=proposed,
        )
        findings = _validate_action(invalid, base_packet, base_context, NOW)
        assert any(item.code == "ACTION_DIRECTION_INVALID" for item in findings)
    results["wrong_direction_fuzz"] = {
        "cases": fuzz_count,
        "seconds": round(perf_counter() - fuzz_start, 4),
    }

    naive_context = context().model_copy(
        update={"valid_until": datetime(2026, 8, 6, 12, 0, 0)}
    )
    naive_report = _validate([action()], source_context=naive_context)
    assert naive_report.outcome == ValidationOutcome.BLOCKED
    assert "AD_CONTEXT_TIMEZONE_MISSING" in _codes(naive_report)
    results["naive_datetime"] = "BLOCKED_NO_CRASH"

    metric_copy = packet()
    sample = metric_copy.metrics[0].samples[0].model_copy(
        update={
            "window": MetricWindow.D3,
            "impressions": 100,
            "clicks": 200,
            "orders": Decimal("300"),
        }
    )
    metric_copy.metrics[0] = metric_copy.metrics[0].model_copy(
        update={"samples": [sample]}
    )
    metric_report = assess_data_quality(metric_copy)
    assert metric_report.status.value == "DQ_BLOCKED"
    assert "IMPOSSIBLE_METRIC_FUNNEL" in _codes(metric_report)
    assert "METRIC_WINDOW_LENGTH_MISMATCH" in _codes(metric_report)
    results["metric_model_copy_bypass"] = "DQ_BLOCKED"

    rules = load_rules(ROOT / "new_product_module/config/category_rules.example.yaml")
    non_rug = run_new_product_pipeline(
        {"category": "office_chair", "order_target_daily": 1, "size_spec": "5x7"},
        [],
        rules,
    )
    assert any(item.source_step == "scope_gate" for item in non_rug.blocked_items)
    results["non_rug_scope"] = "BLOCKED"

    rejected_budgets = 0
    for value in (-2, 0):
        try:
            ProductInfo(
                category="rug",
                order_target_daily=1,
                ad_group_order_target=value,
                size_spec="5x7",
            )
        except ValidationError:
            rejected_budgets += 1
    assert rejected_budgets == 2
    results["nonpositive_budget_targets"] = "2/2_REJECTED"

    action_count = 50_000
    actions = [
        action(action_id=f"LOAD-{index:06d}", object_id=f"T-{index:06d}")
        for index in range(action_count)
    ]
    arbitration_start = perf_counter()
    arbitration = arbitrate_actions("BATCH-001", actions)
    arbitration_seconds = perf_counter() - arbitration_start
    assert len(arbitration.selected_actions) == action_count
    assert not arbitration.conflicts
    assert arbitration_seconds < 5.0
    results["arbitration_load"] = {
        "actions": action_count,
        "seconds": round(arbitration_seconds, 4),
    }

    dq_iterations = 5_000
    quality_packet = packet()
    quality_start = perf_counter()
    for _ in range(dq_iterations):
        assert assess_data_quality(quality_packet).status.value == "DQ_PASS"
    results["data_quality_replay"] = {
        "iterations": dq_iterations,
        "seconds": round(perf_counter() - quality_start, 4),
    }

    adapter_start = perf_counter()
    joined, adapter_issues = load_rug_keyword_evidence(
        ROOT / "reference/rug-aba",
        ROOT
        / "reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx",
    )
    adapter_seconds = perf_counter() - adapter_start
    assert joined
    assert adapter_seconds < 15.0
    results["real_reference_adapter"] = {
        "joined": len(joined),
        "issues": len(adapter_issues),
        "seconds": round(adapter_seconds, 4),
    }

    with TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        aba = temp / "aba.xlsx"
        history = temp / "history.xlsx"
        _write_aba(aba, rank=100)
        _write_history(history)
        duplicate_rows, duplicate_issues = load_rug_keyword_evidence(aba, history)
        assert duplicate_rows[0]["clicks"] == 101
        assert duplicate_rows[0]["orders"] == 10
        assert any(
            issue["code"] == "HISTORY_DUPLICATE_TERMS_AGGREGATED"
            for issue in duplicate_issues
        )

        _write_aba(aba, rank=100.9)
        try:
            load_rug_keyword_evidence(aba, history)
        except ValueError as exc:
            assert "不得截断小数" in str(exc)
        else:
            raise AssertionError("fractional ABA rank was not rejected")
    results["history_duplicate_and_fractional"] = "PASS"

    print(json.dumps({"status": "PASS", "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
