#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.ad_report_aggregator.aggregator import (
    DEFAULT_CONFIG,
    build_packet,
    load_json,
    write_outputs,
)
from tools.ad_report_aggregator.synthetic import REPORT_FILES, create_synthetic_reports


def assert_status(source_dir: Path, context_path: Path, expected: str) -> None:
    _, support = build_packet(
        source_dir,
        load_json(context_path),
        load_json(DEFAULT_CONFIG),
    )
    actual = support["dq_report"].status.value
    if actual != expected:
        raise AssertionError(f"expected {expected}, got {actual}")


def main() -> int:
    parser = argparse.ArgumentParser(description="V2.0 广告报表聚合工具压力测试")
    parser.add_argument(
        "--output-dir",
        help="保留有效样本的聚合输出；不提供时只在临时目录测试。",
    )
    parser.add_argument(
        "--render-previews",
        action="store_true",
        help="输出并渲染十个工作表，用于发布前视觉验收。",
    )
    args = parser.parse_args()

    temp_root = Path(tempfile.mkdtemp(prefix="luyao_ad_aggregation_stress_"))
    started = time.perf_counter()
    try:
        valid_dir, valid_context = create_synthetic_reports(temp_root / "valid")
        packet, support = build_packet(
            valid_dir,
            load_json(valid_context),
            load_json(DEFAULT_CONFIG),
        )
        if support["dq_report"].status.value != "DQ_PASS":
            raise AssertionError("valid six-report sample did not pass")

        replay_ids = set()
        for _ in range(50):
            replay_packet, replay_support = build_packet(
                valid_dir,
                load_json(valid_context),
                load_json(DEFAULT_CONFIG),
            )
            if replay_support["dq_report"].status.value != "DQ_PASS":
                raise AssertionError("deterministic replay failed")
            replay_ids.add(replay_packet.metadata.data_snapshot_id)
        if replay_ids != {packet.metadata.data_snapshot_id}:
            raise AssertionError("data_snapshot_id is not deterministic")

        scenarios = [
            ("mismatch", {"summary_spend_delta": 1}),
            ("duplicate_grain", {"duplicate_daily_row": True}),
            ("bad_currency", {"currency": "CNY"}),
            ("short_window", {"days": 29}),
            ("multi_ad_group", {"extra_ad_group": True}),
            ("malformed_metric", {"malformed_clicks": True}),
            ("attribution_mismatch", {"attribution_window_days": 14}),
        ]
        for name, kwargs in scenarios:
            source_dir, context_path = create_synthetic_reports(temp_root / name, **kwargs)
            assert_status(source_dir, context_path, "DQ_BLOCKED")

        missing_dir, missing_context = create_synthetic_reports(temp_root / "missing")
        (missing_dir / REPORT_FILES["sp_placement"]).unlink()
        assert_status(missing_dir, missing_context, "DQ_BLOCKED")

        duplicate_file_dir, duplicate_file_context = create_synthetic_reports(
            temp_root / "duplicate_file"
        )
        shutil.copy2(
            duplicate_file_dir / REPORT_FILES["sp_search_terms_summary"],
            duplicate_file_dir / "搜索词汇总_副本.csv",
        )
        assert_status(duplicate_file_dir, duplicate_file_context, "DQ_BLOCKED")

        capacity_dir, capacity_context = create_synthetic_reports(
            temp_root / "capacity", term_count=500
        )
        capacity_started = time.perf_counter()
        capacity_packet, capacity_support = build_packet(
            capacity_dir,
            load_json(capacity_context),
            load_json(DEFAULT_CONFIG),
        )
        capacity_elapsed = time.perf_counter() - capacity_started
        if capacity_support["dq_report"].status.value != "DQ_PASS":
            raise AssertionError("15,000-row capacity sample did not pass")
        if len(capacity_packet.search_terms) != 500:
            raise AssertionError("capacity search-term count mismatch")

        if args.output_dir:
            output_dir = Path(args.output_dir).expanduser().resolve()
            write_outputs(
                packet,
                support,
                output_dir,
                workbook=True,
                render_previews=args.render_previews,
            )

        elapsed = time.perf_counter() - started
        print("广告报表聚合压力测试 PASS")
        print("确定性重放: 50/50")
        print("对抗场景: 9/9 正确阻断")
        print(f"容量样本: 15,000 日明细行 / 500 搜索词 / {capacity_elapsed:.3f} 秒")
        print(f"总耗时: {elapsed:.3f} 秒")
        return 0
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
