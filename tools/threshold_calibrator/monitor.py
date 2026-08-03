from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .calibrator import build_candidate_package, load_config, read_samples, write_outputs


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MONITOR_CONFIG = ROOT / "config/threshold_monitoring.json"


def load_monitor_config(path: Path = DEFAULT_MONITOR_CONFIG) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    schedule = config.get("schedule", {})
    expected_schedule = {
        "frequency": "WEEKLY",
        "weekday": "MONDAY",
        "local_time": "09:00",
        "timezone_mode": "INSTALLATION_LOCAL_TIME",
        "automation_kind": "HEARTBEAT",
        "duplicate_policy": "ONE_ACTIVE_MONITOR_PER_PROJECT",
    }
    for field, expected in expected_schedule.items():
        if schedule.get(field) != expected:
            raise ValueError(f"候选阈值监控schedule.{field}必须为{expected}")
    execution = config.get("execution", {})
    if execution.get("active_backend") != "LOCAL_HEARTBEAT":
        raise ValueError("当前发布只允许LOCAL_HEARTBEAT作为活动调度后端")
    for name in ("cloud_runner",):
        if execution.get(name, {}).get("status") != "PLACEHOLDER_NOT_ACTIVE":
            raise ValueError(f"{name}尚未实现，必须保持PLACEHOLDER_NOT_ACTIVE")
    sources = config.get("data_sources", {})
    if sources.get("local_directory", {}).get("status") != "ACTIVE":
        raise ValueError("本地阈值历史目录必须保持ACTIVE")
    cloud = sources.get("cloud_storage", {})
    if cloud.get("status") != "PLACEHOLDER_NOT_ACTIVE":
        raise ValueError("云存储连接器尚未实现，必须保持PLACEHOLDER_NOT_ACTIVE")
    if cloud.get("read_only") is not True:
        raise ValueError("未来云存储接入必须保持只读")
    return config


def local_source_dir(config: dict[str, Any], project_root: Path = ROOT) -> Path:
    relative = Path(config["data_sources"]["local_directory"]["path"])
    if relative.is_absolute():
        raise ValueError("本地历史目录必须使用相对项目路径，保证可移植")
    resolved = (project_root / relative).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError("本地历史目录不得逃逸项目根目录") from exc
    return resolved


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": "1.0", "notified_candidate_ids": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = data.get("notified_candidate_ids")
    if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
        raise ValueError("提醒状态文件notified_candidate_ids必须为字符串数组")
    return data


def evaluate(
    source_dir: Path,
    output_dir: Path,
    state_path: Path,
    config_path: Path,
    monitor_metadata: dict[str, Any] | None = None,
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
    if monitor_metadata is not None:
        result["monitoring"] = monitor_metadata
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
    parser.add_argument("--monitor-config")
    parser.add_argument("--mark-notified")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = ROOT
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
    monitor_config_path = Path(
        args.monitor_config or DEFAULT_MONITOR_CONFIG
    ).expanduser().resolve()
    monitor_config = load_monitor_config(monitor_config_path)
    source_dir = (
        Path(args.source_dir).expanduser().resolve()
        if args.source_dir
        else local_source_dir(monitor_config, root)
    )
    config_path = Path(
        args.config or root / "config/threshold_calibration.json"
    ).expanduser().resolve()
    result = evaluate(
        source_dir,
        output_dir,
        state_path,
        config_path,
        monitor_metadata={
            "config_path": str(monitor_config_path),
            "schedule": monitor_config["schedule"],
            "active_backend": monitor_config["execution"]["active_backend"],
            "cloud_storage_status": monitor_config["data_sources"][
                "cloud_storage"
            ]["status"],
            "cloud_runner_status": monitor_config["execution"]["cloud_runner"][
                "status"
            ],
        },
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
