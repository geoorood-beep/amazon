from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .calibrator import build_candidate_package, load_config, read_samples, write_outputs


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": "1.0", "notified_candidate_ids": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = data.get("notified_candidate_ids")
    if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
        raise ValueError("提醒状态文件notified_candidate_ids必须为字符串数组")
    return data


def evaluate(
    source_dir: Path, output_dir: Path, state_path: Path, config_path: Path
) -> dict[str, Any]:
    config = load_config(config_path)
    rows, evidence = read_samples(source_dir)
    if not rows:
        result = {
            "monitor_status": "NO_INPUT",
            "should_notify": False,
            "reason": "本地历史输入目录没有阈值校准CSV",
            "source_dir": str(source_dir),
        }
    else:
        package = build_candidate_package(rows, evidence, config)
        outputs = write_outputs(package, output_dir)
        state = _read_state(state_path)
        candidate_id = package["candidate_id"]
        eligible = int(package["eligible_segment_count"]) > 0
        already_notified = candidate_id in set(state["notified_candidate_ids"])
        result = {
            "monitor_status": (
                "NEW_CANDIDATE"
                if eligible and not already_notified
                else "ALREADY_NOTIFIED"
                if eligible
                else "NOT_ELIGIBLE"
            ),
            "candidate_id": candidate_id,
            "candidate_sha256": json.loads(
                outputs["status"].read_text(encoding="utf-8")
            )["candidate_sha256"],
            "eligible_segment_count": package["eligible_segment_count"],
            "risk_candidate_count": package["risk_candidate_count"],
            "historically_better_segment_count": package[
                "historically_better_segment_count"
            ],
            "should_notify": eligible and not already_notified,
            "already_notified": already_notified,
            "candidate_path": str(outputs["candidate"]),
            "markdown_path": str(outputs["markdown"]),
            "state_path": str(state_path),
            "auto_apply": False,
            "human_approval_required": True,
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    monitor_path = output_dir / "monitor_status.json"
    monitor_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    result["monitor_status_path"] = str(monitor_path)
    return result


def mark_notified(candidate_id: str, state_path: Path, status_path: Path) -> dict[str, Any]:
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("candidate_id") != candidate_id:
        raise ValueError("待标记Candidate ID与当前监控结果不一致")
    if not status.get("should_notify"):
        raise ValueError("当前候选未达到提醒条件，不得标记已提醒")
    state = _read_state(state_path)
    ids = list(dict.fromkeys([*state["notified_candidate_ids"], candidate_id]))
    state = {"schema_version": "1.0", "notified_candidate_ids": ids[-200:]}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return state


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="监控Rug候选阈值并抑制重复提醒")
    parser.add_argument("--source-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--state")
    parser.add_argument("--config")
    parser.add_argument("--mark-notified")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    output_dir = Path(
        args.output_dir or root / "outputs/threshold-calibration/latest"
    ).expanduser().resolve()
    state_path = Path(
        args.state or root / "outputs/threshold-calibration/notified_candidates.json"
    ).expanduser().resolve()
    if args.mark_notified:
        state = mark_notified(
            args.mark_notified,
            state_path,
            output_dir / "threshold_calibration_status.json",
        )
        print(json.dumps(state, ensure_ascii=False))
        return 0
    source_dir = Path(
        args.source_dir or root / "imports/threshold-calibration"
    ).expanduser().resolve()
    config_path = Path(
        args.config or root / "config/threshold_calibration.json"
    ).expanduser().resolve()
    result = evaluate(source_dir, output_dir, state_path, config_path)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
