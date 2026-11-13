from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .calibrator import sha256_file


ALLOWED_DECISIONS = {"APPROVED", "REVISED", "REJECTED", "INSUFFICIENT_DATA"}


def build_change_set(candidate_path: Path, approval_path: Path) -> dict[str, Any]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    decision = str(approval.get("decision", "")).strip().upper()
    if decision not in ALLOWED_DECISIONS:
        raise ValueError("人工决定只允许APPROVED/REVISED/REJECTED/INSUFFICIENT_DATA")
    if approval.get("candidate_id") != candidate.get("candidate_id"):
        raise ValueError("批准记录Candidate ID与候选包不一致")
    actual_sha = sha256_file(candidate_path)
    if approval.get("candidate_sha256") != actual_sha:
        raise ValueError("批准记录中的候选文件SHA-256不一致")
    if not str(approval.get("reviewer", "")).strip():
        raise ValueError("批准记录缺少reviewer")
    if not str(approval.get("approved_scope", "")).strip():
        raise ValueError("批准记录缺少approved_scope")
    try:
        reviewed_at = datetime.fromisoformat(str(approval.get("reviewed_at", "")))
    except ValueError as exc:
        raise ValueError("reviewed_at必须是ISO-8601时间") from exc
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise ValueError("reviewed_at必须包含时区")
    approved_segments = [
        item
        for item in candidate.get("segments", [])
        if item.get("eligibility_status")
        in {"REFERENCE_CANDIDATE", "HIGH_CONFIDENCE_CANDIDATE"}
        and item.get("proof_status") == "HISTORICALLY_BETTER_CANDIDATE"
    ]
    if decision == "APPROVED" and not approved_segments:
        raise ValueError("候选包没有历史留出验证更优的分组，不得批准")
    return {
        "schema_version": "1.0",
        "change_set_type": "THRESHOLD_CALIBRATION_APPROVAL",
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": actual_sha,
        "decision": decision,
        "reviewer": approval["reviewer"],
        "reviewed_at": approval["reviewed_at"],
        "approved_scope": approval["approved_scope"],
        "notes": approval.get("notes", ""),
        "eligible_segments": [item["segment_id"] for item in approved_segments],
        "status": (
            "HUMAN_APPROVED_PENDING_REGRESSION"
            if decision == "APPROVED"
            else f"HUMAN_{decision}"
        ),
        "auto_apply": False,
        "required_next_steps": [
            "人工维护thresholds/正式标准",
            "登记来源SHA-256和适用粒度",
            "运行边界、回放、Validator和压力测试",
            "重建V2.0 manifest",
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="验证候选阈值人工批准并生成待回归Change Set")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--approval", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candidate_path = Path(args.candidate).expanduser().resolve()
    approval_path = Path(args.approval).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    change_set = build_change_set(candidate_path, approval_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(change_set, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Decision: {change_set['decision']}")
    print(f"Status: {change_set['status']}")
    print(f"Auto apply: {change_set['auto_apply']}")
    print(f"Change Set: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
