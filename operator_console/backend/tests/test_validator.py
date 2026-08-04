from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from validator import validate_operator_result  # noqa: E402
from agents_context import build_agents_analysis_context, build_tool_receipt, canonical_digest, source_record  # noqa: E402


ROOT = BACKEND.parents[1]


def valid_result() -> dict:
    return {
        "schema_version": "1.0",
        "job_id": "job-12345678",
        "intent": "OLD_PRODUCT_OPTIMIZATION",
        "category": "rug",
        "status": "READY_FOR_HUMAN_REVIEW",
        "title": "候选建议",
        "executive_summary": "仅供人工确认",
        "primary_issue": None,
        "recommendations": [
            {
                "priority": "P1",
                "action": "人工检查预算",
                "reason": "证据满足合同",
                "evidence": "packet.json",
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
            "codex_run_id": "pending",
            "agents_context_digest": None,
            "sources_read": [],
            "tool_receipt_ids": [],
        },
        "safety": {
            "execution_allowed": False,
            "auto_apply": False,
            "human_approval_required": True,
            "validator_status": "CANDIDATE_ONLY",
        },
        "next_steps": ["人工确认"],
    }


class OperatorValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.request = {
            "job_id": "job-12345678",
            "intent": "OLD_PRODUCT_OPTIMIZATION",
            "fields": {},
        }
        self.request["routing"] = json.loads((ROOT / "config/operator_intents.json").read_text())["intents"][self.request["intent"]]
        self.preprocessing = self._ready_preprocessing(self.request)

    def _ready_preprocessing(self, request: dict, **extra: object) -> dict:
        preprocessing = {"status": "READY_FOR_ANALYSIS", "artifacts": [], "input_artifacts": [], **extra}
        preprocessing["tool_receipts"] = [build_tool_receipt(ROOT, request, preprocessing)]
        preprocessing["agents_context"] = build_agents_analysis_context(ROOT, request, preprocessing)
        return preprocessing

    def _bind_codex_receipt(self, result: dict, request: dict, preprocessing: dict) -> None:
        context = preprocessing["agents_context"]
        result["provenance"] = {
            "decision_engine": "CODEX_AGENTS",
            "codex_invoked": True,
            "codex_run_id": "test-codex-run",
            "agents_context_digest": context["context_digest"],
            "sources_read": context["required_codex_sources"],
            "tool_receipt_ids": context["tool_receipt_ids"],
        }
        output = Path(self.temp_dir.name) / f"{request['intent']}.json"
        output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        receipt = {
            "schema_version": "2.1",
            "codex_run_id": "test-codex-run",
            "codex_invoked": True,
            "status": "SUCCESS",
            "exit_code": 0,
            "prompt_sha256": "a" * 64,
            "agents_context_digest": context["context_digest"],
            "tool_receipt_ids": context["tool_receipt_ids"],
            "output_path": str(output),
            "output_sha256": source_record(ROOT, str(output), "codex_output", external=True)["sha256"],
        }
        receipt["receipt_id"] = canonical_digest(receipt)
        preprocessing["codex_invocation_receipt"] = receipt

    def test_valid_candidate_passes_without_execution_permission(self) -> None:
        result = valid_result()
        self._bind_codex_receipt(result, self.request, self.preprocessing)
        validation = validate_operator_result(result, self.request, self.preprocessing)
        self.assertEqual(validation["outcome"], "PASS_CANDIDATE_ONLY")
        self.assertFalse(validation["execution_allowed"])

    def test_forged_auto_apply_is_blocked(self) -> None:
        result = deepcopy(valid_result())
        self._bind_codex_receipt(result, self.request, self.preprocessing)
        result["safety"]["auto_apply"] = True
        validation = validate_operator_result(result, self.request, self.preprocessing)
        self.assertEqual(validation["outcome"], "BLOCKED")
        self.assertIn("AUTO_APPLY_FORGED", {item["code"] for item in validation["findings"]})

    def test_blocked_preprocessing_cannot_be_promoted(self) -> None:
        validation = validate_operator_result(valid_result(), self.request, {"status": "DATA_BLOCKED"})
        self.assertEqual(validation["outcome"], "BLOCKED")
        self.assertIn("BLOCKED_DATA_PROMOTED", {item["code"] for item in validation["findings"]})

    def test_non_rug_result_is_blocked(self) -> None:
        result = deepcopy(valid_result())
        self._bind_codex_receipt(result, self.request, self.preprocessing)
        result["category"] = "office_chair"
        validation = validate_operator_result(result, self.request, self.preprocessing)
        self.assertEqual(validation["outcome"], "BLOCKED")
        self.assertIn("NON_RUG_RESULT", {item["code"] for item in validation["findings"]})

    def test_new_product_batch_count_and_unique_asins_are_validated(self) -> None:
        result = valid_result()
        result["intent"] = "NEW_PRODUCT_PROMOTION"
        request = {
            "job_id": "job-12345678",
            "intent": "NEW_PRODUCT_PROMOTION",
            "fields": {
                "products_json": '[{"asin":"B0ABC12345"},{"asin":"B0XYZ98765"}]',
            },
        }
        request["routing"] = json.loads((ROOT / "config/operator_intents.json").read_text())["intents"][request["intent"]]
        preprocessing = self._ready_preprocessing(
            request,
            match_type_data_status="READY",
            input_mode="manual",
            product_count=2,
            analysis_asins=["B0ABC12345", "B0XYZ98765"],
        )
        self._bind_codex_receipt(result, request, preprocessing)
        validation = validate_operator_result(result, request, preprocessing)
        self.assertEqual(validation["outcome"], "PASS_CANDIDATE_ONLY")

        preprocessing["analysis_asins"] = ["B0ABC12345", "B0ABC12345"]
        validation = validate_operator_result(result, request, preprocessing)
        self.assertIn("NEW_PRODUCT_ASIN_DUPLICATE", {item["code"] for item in validation["findings"]})

    def test_new_product_pending_match_type_sources_are_blocked(self) -> None:
        result = valid_result()
        result["intent"] = "NEW_PRODUCT_PROMOTION"
        request = {
            "job_id": "job-12345678",
            "intent": "NEW_PRODUCT_PROMOTION",
            "fields": {"products_json": '[{"asin":"B0ABC12345"}]'},
        }
        request["routing"] = json.loads((ROOT / "config/operator_intents.json").read_text())["intents"][request["intent"]]
        preprocessing = self._ready_preprocessing(
            request,
            match_type_data_status="PENDING_SOURCE",
            input_mode="manual",
            product_count=1,
            analysis_asins=["B0ABC12345"],
        )
        self._bind_codex_receipt(result, request, preprocessing)
        validation = validate_operator_result(result, request, preprocessing)
        self.assertIn("MATCH_TYPE_DATA_PENDING", {item["code"] for item in validation["findings"]})

    def test_ready_analysis_without_agents_context_is_blocked(self) -> None:
        validation = validate_operator_result(
            valid_result(),
            self.request,
            {"status": "READY_FOR_ANALYSIS"},
        )
        self.assertIn("AGENTS_CONTEXT_MISSING", {item["code"] for item in validation["findings"]})

    def test_codex_declared_validator_blocked_cannot_complete(self) -> None:
        result = valid_result()
        result["status"] = "VALIDATOR_BLOCKED"
        validation = validate_operator_result(result, self.request, self.preprocessing)
        self.assertIn("RESULT_NOT_READY", {item["code"] for item in validation["findings"]})


if __name__ == "__main__":
    unittest.main()
