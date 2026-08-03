from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from validator import validate_operator_result  # noqa: E402


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
                "risk": "需人工确认",
                "approval_required": True,
            }
        ],
        "missing_inputs": [],
        "artifacts": [],
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
        self.request = {
            "job_id": "job-12345678",
            "intent": "OLD_PRODUCT_OPTIMIZATION",
        }
        self.preprocessing = {"status": "READY_FOR_ANALYSIS"}

    def test_valid_candidate_passes_without_execution_permission(self) -> None:
        validation = validate_operator_result(valid_result(), self.request, self.preprocessing)
        self.assertEqual(validation["outcome"], "PASS_CANDIDATE_ONLY")
        self.assertFalse(validation["execution_allowed"])

    def test_forged_auto_apply_is_blocked(self) -> None:
        result = deepcopy(valid_result())
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
        result["category"] = "office_chair"
        validation = validate_operator_result(result, self.request, self.preprocessing)
        self.assertEqual(validation["outcome"], "BLOCKED")
        self.assertIn("NON_RUG_RESULT", {item["code"] for item in validation["findings"]})


if __name__ == "__main__":
    unittest.main()
