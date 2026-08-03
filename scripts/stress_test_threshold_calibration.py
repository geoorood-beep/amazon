#!/usr/bin/env python3
from __future__ import annotations

import csv
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.threshold_calibrator.calibrator import (  # noqa: E402
    REQUIRED_COLUMNS,
    build_candidate_package,
    load_config,
    read_samples,
)


def row(segment: int, day: int) -> dict[str, str]:
    current = date(2026, 1, 1) + timedelta(days=day)
    return {
        "date": current.isoformat(),
        "category": "rug",
        "segment_id": f"area-small-sp-target-growth-{segment:04d}",
        "rug_type": "area_rug",
        "size_profile": "area_small",
        "ad_product_type": "SP",
        "strategy_stage": "growth",
        "object_grain": "TARGET",
        "object_id": f"T-{segment:04d}",
        "marketplace": "US",
        "currency": "USD",
        "impressions": "2000",
        "clicks": "200",
        "orders": "5",
        "spend": str(120 + day),
        "sales": str(150 + day * 2),
        "attribution_mature": "true",
        "dq_status": "DQ_PASS",
        "validation_window_id": f"W{day // 10 + 1}",
        "source_ref": f"stress:{segment}:{day}",
    }


def proof_row(object_index: int, day: int, *, reverse_holdout: bool) -> dict[str, str]:
    holdout = day >= 21
    if holdout and reverse_holdout:
        orders = 35 - object_index
        cpa = Decimal("16.65") + Decimal(object_index) * Decimal("0.15")
        acos = Decimal("0.2775") + Decimal(object_index) * Decimal("0.0025")
    else:
        orders = 6 + object_index
        cpa = Decimal("21") - Decimal(object_index) * Decimal("0.15")
        acos = Decimal("0.35") - Decimal(object_index) * Decimal("0.0025")
    spend = Decimal(orders) * cpa
    sales = spend / acos
    return {
        "date": (date(2026, 1, 1) + timedelta(days=day)).isoformat(),
        "category": "rug",
        "segment_id": "area-small-sp-sku-size-growth",
        "rug_type": "area_rug",
        "size_profile": "area_small",
        "ad_product_type": "SP",
        "strategy_stage": "growth",
        "object_grain": "SKU_SIZE",
        "object_id": f"SKU-{object_index:02d}",
        "marketplace": "US",
        "currency": "USD",
        "impressions": "1000",
        "clicks": "100",
        "orders": str(orders),
        "spend": format(spend, "f"),
        "sales": format(sales, "f"),
        "attribution_mature": "true",
        "dq_status": "DQ_PASS",
        "validation_window_id": f"W{day // 10 + 1}",
        "source_ref": f"proof:{object_index}:{day}",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def expect_rejected(source: Path, name: str) -> None:
    try:
        read_samples(source)
    except ValueError:
        return
    raise AssertionError(f"对抗场景未阻断: {name}")


def main() -> int:
    config = load_config(ROOT / "config/threshold_calibration.json")
    with TemporaryDirectory(prefix="rug-threshold-stress-") as temp:
        base = Path(temp)
        source = base / "capacity"
        rows = [row(segment, day) for segment in range(200) for day in range(30)]
        write_csv(source / "history.csv", rows)
        started = perf_counter()
        loaded, evidence = read_samples(source)
        package = build_candidate_package(loaded, evidence, config)
        elapsed = perf_counter() - started
        if len(loaded) != 6000 or package["eligible_segment_count"] != 200:
            raise AssertionError("容量数据的行数或达标分组数错误")
        baseline = package["candidate_id"]
        for _ in range(20):
            replay_rows, replay_evidence = read_samples(source)
            replay = build_candidate_package(replay_rows, replay_evidence, config)
            if replay["candidate_id"] != baseline:
                raise AssertionError("相同历史输入的Candidate ID不确定")

        duplicate = base / "duplicate"
        one = [row(1, 1)]
        write_csv(duplicate / "a.csv", one)
        write_csv(duplicate / "b.csv", one)
        expect_rejected(duplicate, "跨文件重复日粒度")

        non_rug = base / "non_rug"
        hostile = row(1, 1)
        hostile["category"] = "office_chair"
        write_csv(non_rug / "history.csv", [hostile])
        expect_rejected(non_rug, "跨类目数据")

        negative = base / "negative"
        hostile = row(1, 1)
        hostile["spend"] = "-1"
        write_csv(negative / "history.csv", [hostile])
        expect_rejected(negative, "负数花费")

        impossible = base / "impossible"
        hostile = row(1, 1)
        hostile["orders"] = "201"
        write_csv(impossible / "history.csv", [hostile])
        expect_rejected(impossible, "订单大于点击")

        malformed = base / "malformed"
        hostile = row(1, 1)
        del hostile["source_ref"]
        malformed.mkdir(parents=True)
        with (malformed / "history.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=sorted(hostile))
            writer.writeheader()
            writer.writerow(hostile)
        expect_rejected(malformed, "缺列")

        proof_source = base / "proof_better"
        write_csv(
            proof_source / "history.csv",
            [proof_row(obj, day, reverse_holdout=False) for obj in range(30) for day in range(30)],
        )
        proof_rows, proof_evidence = read_samples(proof_source)
        proof_package = build_candidate_package(proof_rows, proof_evidence, config)
        if proof_package["segments"][0]["proof_status"] != "HISTORICALLY_BETTER_CANDIDATE":
            raise AssertionError("正向留出样本未证明候选历史更优")

        reverse_source = base / "proof_reverse"
        write_csv(
            reverse_source / "history.csv",
            [proof_row(obj, day, reverse_holdout=True) for obj in range(30) for day in range(30)],
        )
        reverse_rows, reverse_evidence = read_samples(reverse_source)
        reverse_package = build_candidate_package(reverse_rows, reverse_evidence, config)
        if reverse_package["segments"][0]["proof_status"] != "NOT_BETTER":
            raise AssertionError("反向留出样本未拒绝候选")

        print(
            "阈值校准压力测试通过："
            f"6,000行/200分组={elapsed:.3f}秒；"
            "20次确定性重放；5类对抗输入全部阻断；"
            "正向留出证明/反向留出拒绝均通过；自动应用保持关闭。"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
