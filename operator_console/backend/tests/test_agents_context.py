from __future__ import annotations

import json
from pathlib import Path
import sys


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND))

from agents_context import build_agents_analysis_context, build_tool_receipt  # noqa: E402


def test_new_product_context_resolves_agents_rules_thresholds_data_and_tools() -> None:
    routing = json.loads((ROOT / "config/operator_intents.json").read_text(encoding="utf-8"))["intents"][
        "NEW_PRODUCT_PROMOTION"
    ]
    request = {"job_id": "context-test", "intent": "NEW_PRODUCT_PROMOTION", "routing": routing, "fields": {}}
    preprocessing = {"status": "READY_FOR_ANALYSIS", "artifacts": [], "input_artifacts": []}
    preprocessing["tool_receipts"] = [build_tool_receipt(ROOT, request, preprocessing)]
    context = build_agents_analysis_context(ROOT, request, preprocessing)
    assert context["route_status"] == "READY"
    assert context["architecture_layer_coverage"] == {"available": 8, "required": 8}
    assert len(context["sources"]["architecture"]) == 8
    assert context["agents_entry"] == "AGENTS.md"
    assert context["sources"]["rules"]
    assert context["sources"]["thresholds"]
    assert context["sources"]["knowledge"]
    assert context["sources"]["tools"]
    assert context["sources"]["configs"]
    assert all(item["status"] == "AVAILABLE" for group in context["sources"].values() for item in group)


def test_empty_or_tampered_route_is_fail_closed() -> None:
    request = {"job_id": "context-test", "intent": "OLD_PRODUCT_OPTIMIZATION", "routing": {}, "fields": {}}
    preprocessing = {"status": "READY_FOR_ANALYSIS", "artifacts": [], "input_artifacts": []}
    preprocessing["tool_receipts"] = [build_tool_receipt(ROOT, request, preprocessing)]
    context = build_agents_analysis_context(ROOT, request, preprocessing)
    assert context["route_status"] == "BLOCKED"
    assert "ROUTE_MISMATCH" in context["blocking_codes"]
