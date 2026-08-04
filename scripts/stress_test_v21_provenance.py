#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "operator_console/backend"
sys.path.insert(0, str(BACKEND))

from agents_context import (  # noqa: E402
    build_agents_analysis_context,
    build_tool_receipt,
    canonical_digest,
    source_record,
)
from validator import validate_operator_result  # noqa: E402


def trusted_request(intent: str) -> dict:
    routes = json.loads((ROOT / "config/operator_intents.json").read_text(encoding="utf-8"))["intents"]
    return {
        "job_id": "v21-provenance-stress",
        "intent": intent,
        "category": "rug",
        "fields": {},
        "routing": routes[intent],
    }


def ready_preprocessing(request: dict) -> dict:
    preprocessing = {"status": "READY_FOR_ANALYSIS", "artifacts": [], "input_artifacts": []}
    preprocessing["tool_receipts"] = [build_tool_receipt(ROOT, request, preprocessing)]
    preprocessing["agents_context"] = build_agents_analysis_context(ROOT, request, preprocessing)
    return preprocessing


def base_result(request: dict, preprocessing: dict) -> dict:
    context = preprocessing["agents_context"]
    return {
        "schema_version": "1.0",
        "job_id": request["job_id"],
        "intent": request["intent"],
        "category": "rug",
        "status": "READY_FOR_HUMAN_REVIEW",
        "title": "候选",
        "executive_summary": "仅供人工确认",
        "primary_issue": None,
        "recommendations": [
            {
                "priority": "P1",
                "action": "人工检查",
                "reason": "压力测试",
                "evidence": "scope rule",
                "evidence_sources": ["rules/core/scope-and-capability.md"],
                "risk": "需人工确认",
                "approval_required": True,
            }
        ],
        "new_product_architecture": [],
        "missing_inputs": [],
        "artifacts": [],
        "provenance": {
            "decision_engine": "CODEX_AGENTS",
            "codex_invoked": True,
            "codex_run_id": "stress-codex-run",
            "agents_context_digest": context["context_digest"],
            "sources_read": context["required_codex_sources"],
            "tool_receipt_ids": context["tool_receipt_ids"],
        },
        "safety": {
            "execution_allowed": False,
            "auto_apply": False,
            "human_approval_required": True,
            "validator_status": "CANDIDATE_ONLY",
        },
        "next_steps": ["人工确认"],
    }


def bind_receipt(result: dict, preprocessing: dict, output: Path) -> None:
    output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    receipt = {
        "schema_version": "2.1",
        "codex_run_id": "stress-codex-run",
        "codex_invoked": True,
        "status": "SUCCESS",
        "exit_code": 0,
        "prompt_sha256": "a" * 64,
        "agents_context_digest": preprocessing["agents_context"]["context_digest"],
        "tool_receipt_ids": preprocessing["agents_context"]["tool_receipt_ids"],
        "output_path": str(output),
        "output_sha256": source_record(ROOT, str(output), "codex_output", external=True)["sha256"],
    }
    receipt["receipt_id"] = canonical_digest(receipt)
    preprocessing["codex_invocation_receipt"] = receipt


def finding_codes(result: dict, request: dict, preprocessing: dict, **kwargs: object) -> set[str]:
    validation = validate_operator_result(result, request, preprocessing, **kwargs)
    return {str(item["code"]) for item in validation["findings"]}


def main() -> int:
    layer_results = {}
    for intent in (
        "NEW_PRODUCT_PROMOTION",
        "OLD_PRODUCT_OPTIMIZATION",
        "AGGREGATE_REPORTS",
        "WEEKLY_REVIEW",
    ):
        request = trusted_request(intent)
        preprocessing = ready_preprocessing(request)
        context = preprocessing["agents_context"]
        layer_results[intent] = {
            "route_status": context["route_status"],
            "coverage": context["architecture_layer_coverage"],
        }

    request = trusted_request("OLD_PRODUCT_OPTIMIZATION")
    preprocessing = ready_preprocessing(request)
    result = base_result(request, preprocessing)
    with tempfile.TemporaryDirectory() as raw_temp:
        output = Path(raw_temp) / "codex_result.json"
        bind_receipt(result, preprocessing, output)
        baseline = validate_operator_result(result, request, preprocessing)["outcome"]

        forged_passes = 0
        start = time.perf_counter()
        for index in range(10_000):
            forged = deepcopy(preprocessing)
            forged["agents_context"] = {
                "route_status": "READY",
                "intent": request["intent"],
                "agents_entry": f"FORGED-{index}",
                "sources": {},
                "context_digest": "0" * 64,
            }
            if validate_operator_result(result, request, forged)["outcome"] != "BLOCKED":
                forged_passes += 1
        forged_seconds = time.perf_counter() - start

        tampered_tool = deepcopy(preprocessing)
        tampered_tool["tool_receipts"][0]["receipt_id"] = "f" * 64
        tool_codes = finding_codes(result, request, tampered_tool)

        missing_source_result = deepcopy(result)
        missing_source_result["provenance"]["sources_read"] = missing_source_result["provenance"]["sources_read"][1:]
        bind_receipt(missing_source_result, preprocessing, output)
        source_codes = finding_codes(missing_source_result, request, preprocessing)

        bad_evidence_result = deepcopy(result)
        bad_evidence_result["recommendations"][0]["evidence_sources"] = ["outside/not-registered.md"]
        bind_receipt(bad_evidence_result, preprocessing, output)
        evidence_codes = finding_codes(bad_evidence_result, request, preprocessing)

        bind_receipt(result, preprocessing, output)
        artifact = Path(raw_temp) / "SP广告优化方案.xlsx"
        artifact.write_bytes(b"validated-artifact")
        final_result = deepcopy(result)
        final_result["artifacts"] = [str(artifact)]
        preprocessing["final_artifact_receipts"] = [
            source_record(ROOT, str(artifact), "final_artifact", external=True)
        ]
        final_baseline = validate_operator_result(
            final_result, request, preprocessing, require_final_artifacts=True
        )["outcome"]
        artifact_stat = artifact.stat()
        artifact.write_bytes(b"tamperedx-artifacX")
        assert artifact.stat().st_size == artifact_stat.st_size
        os.utime(artifact, ns=(artifact_stat.st_atime_ns, artifact_stat.st_mtime_ns))
        artifact_codes = finding_codes(
            final_result,
            request,
            preprocessing,
            require_final_artifacts=True,
        )

        bind_receipt(result, preprocessing, output)
        output.write_text("{}", encoding="utf-8")
        output_codes = finding_codes(result, request, preprocessing)

    passed = (
        baseline == "PASS_CANDIDATE_ONLY"
        and all(item["route_status"] == "READY" and item["coverage"] == {"available": 8, "required": 8} for item in layer_results.values())
        and forged_passes == 0
        and "TOOL_RECEIPT_MISMATCH" in tool_codes
        and "CODEX_SOURCE_COVERAGE_MISMATCH" in source_codes
        and "RECOMMENDATION_EVIDENCE_UNREGISTERED" in evidence_codes
        and final_baseline == "PASS_CANDIDATE_ONLY"
        and "FINAL_ARTIFACT_SHA_MISMATCH" in artifact_codes
        and "CODEX_OUTPUT_SHA_MISMATCH" in output_codes
    )
    print(
        json.dumps(
            {
                "status": "PASS" if passed else "FAIL",
                "baseline": baseline,
                "architecture_layers": layer_results,
                "forged_contexts": {
                    "cases": 10_000,
                    "passed": forged_passes,
                    "seconds": round(forged_seconds, 4),
                },
                "tampered_tool_receipt": sorted(tool_codes),
                "missing_codex_source": sorted(source_codes),
                "unregistered_evidence": sorted(evidence_codes),
                "final_artifact_baseline": final_baseline,
                "tampered_final_artifact": sorted(artifact_codes),
                "tampered_codex_output": sorted(output_codes),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
