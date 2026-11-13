#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_ads.contracts import (
    AdContext,
    AdDecisionPacket,
    AdPlanCandidate,
    AdReviewSignal,
    CandidateAction,
    ExecutionConfirmation,
    ReviewInput,
    RulePackageReference,
    ValidationReport,
)
from ai_ads.decision_logic import LowSampleInput, OverallStateInput, TrendInput


OUTPUT_DIR = ROOT / "ai_ads/schemas"
MODELS = {
    "ad-context.schema.json": AdContext,
    "ad-decision-packet.schema.json": AdDecisionPacket,
    "rule-package-reference.schema.json": RulePackageReference,
    "candidate-action.schema.json": CandidateAction,
    "ad-plan-candidate.schema.json": AdPlanCandidate,
    "validation-report.schema.json": ValidationReport,
    "execution-confirmation.schema.json": ExecutionConfirmation,
    "review-input.schema.json": ReviewInput,
    "ad-review-signal.schema.json": AdReviewSignal,
    "low-sample-input.schema.json": LowSampleInput,
    "overall-state-input.schema.json": OverallStateInput,
    "trend-input.schema.json": TrendInput,
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for file_name, model in MODELS.items():
        payload = model.model_json_schema()
        output = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        (OUTPUT_DIR / file_name).write_text(output + "\n", encoding="utf-8")
    print(f"已导出{len(MODELS)}份V2接口Schema到{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
