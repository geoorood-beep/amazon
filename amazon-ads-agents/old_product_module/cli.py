"""喂水器老品广告方案生成。

用法（在 old_product_module 目录下）：
    py cli.py --reports ../ops/pet_water_fountain/weekly/2026-W47/raw --profile profile.json
默认输出到报表目录同级的 plan/，成熟度默认读取 ops/pet_water_fountain/README.md。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine.loaders import load_reports  # noqa: E402
from engine.render import render_order, render_report, write_csv  # noqa: E402
from engine.rules import FountainEngine  # noqa: E402

DEFAULT_OPS = HERE.parent / "ops" / "pet_water_fountain"


def read_maturity(ops_dir: Path) -> str:
    readme = ops_dir / "README.md"
    if readme.exists():
        m = re.search(r"当前成熟度：`(L\d)`", readme.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "L0"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="喂水器老品广告方案引擎")
    p.add_argument("--reports", required=True, type=Path, help="领星导出报表所在目录（weekly/<周>/raw）")
    p.add_argument("--profile", required=True, type=Path, help="产品档案 JSON，参考 profile.example.json")
    p.add_argument("--out", type=Path, help="输出目录，默认 <reports>/../plan")
    p.add_argument("--maturity", choices=["L0", "L1", "L2", "L3", "L4"], help="数据成熟度，默认读 ops README")
    p.add_argument("--config", type=Path, default=HERE / "config" / "pet_water_fountain.json")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    maturity = args.maturity or read_maturity(DEFAULT_OPS)
    out = args.out or args.reports.parent / "plan"
    out.mkdir(parents=True, exist_ok=True)

    rep = load_reports(args.reports)
    engine = FountainEngine(cfg, profile, maturity)
    res = engine.run(rep)

    (out / "方案报告.md").write_text(render_report(res, rep, profile, maturity, engine), encoding="utf-8")
    (out / "执行指令单草稿.md").write_text(render_order(res, profile, maturity, str(out / "方案报告.md")), encoding="utf-8")
    write_csv(res, out / "actions.csv")

    exe = sum(1 for a in res.actions if a.executable)
    print(f"成熟度 {maturity}；已识别报表 {len(rep.files)}/6；可执行动作 {exe} 条；输出目录 {out}")
    for w in rep.warnings:
        print("警告：", w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
