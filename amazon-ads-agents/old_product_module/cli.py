"""老品广告方案生成（多品类通用）。

用法（在 old_product_module 目录下）：
    py cli.py --category pet_water_fountain --reports ../categories/pet_water_fountain/ops/weekly/2026-W47/raw --profile profile.json
品类配置读 categories/<品类>/engine.json，成熟度读 categories/<品类>/ops/README.md，
默认输出到报表目录同级的 plan/。
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
from engine.rules import CategoryEngine  # noqa: E402

CATEGORIES = HERE.parent / "categories"


def read_maturity(ops_dir: Path) -> str:
    readme = ops_dir / "README.md"
    if readme.exists():
        m = re.search(r"当前成熟度：`(L\d)`", readme.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "L0"


def load_category_config(category: str, config: Path | None = None) -> dict:
    path = config or CATEGORIES / category / "engine.json"
    if not path.exists():
        opened = sorted(p.parent.name for p in CATEGORIES.glob("*/engine.json") if not p.parent.name.startswith("_"))
        raise SystemExit(f"品类 {category!r} 没有 engine.json（{path}）。已配置引擎的品类：{opened}。"
                         f"新品类请按 categories/README.md 的开通步骤复制 _template/。")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if not cfg.get("models"):
        raise SystemExit(f"品类 {category!r} 的 engine.json 还没有配置任何型号阈值（models 为空），"
                         f"请先补 categories/{category}/thresholds.md 和 engine.json。")
    return cfg


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="UTA-amazon-ads 老品广告方案引擎")
    p.add_argument("--category", default="pet_water_fountain", help="品类 key，见 categories/README.md")
    p.add_argument("--reports", required=True, type=Path, help="领星导出报表所在目录（categories/<品类>/ops/weekly/<周>/raw）")
    p.add_argument("--profile", required=True, type=Path, help="产品档案 JSON，参考 profile.example.json")
    p.add_argument("--out", type=Path, help="输出目录，默认 <reports>/../plan")
    p.add_argument("--maturity", choices=["L0", "L1", "L2", "L3", "L4"], help="数据成熟度，默认读品类 ops/README.md")
    p.add_argument("--config", type=Path, help="覆盖品类 engine.json 路径（一般不用）")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    cfg = load_category_config(args.category, args.config)
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    maturity = args.maturity or read_maturity(CATEGORIES / args.category / "ops")
    out = args.out or args.reports.parent / "plan"
    out.mkdir(parents=True, exist_ok=True)

    rep = load_reports(args.reports)
    engine = CategoryEngine(cfg, profile, maturity)
    res = engine.run(rep)

    (out / "方案报告.md").write_text(render_report(res, rep, profile, maturity, engine), encoding="utf-8")
    (out / "执行指令单草稿.md").write_text(render_order(res, profile, maturity, str(out / "方案报告.md"), category=cfg.get("category", args.category)), encoding="utf-8")
    write_csv(res, out / "actions.csv")

    exe = sum(1 for a in res.actions if a.executable)
    print(f"品类 {args.category}；成熟度 {maturity}；已识别报表 {len(rep.files)}/6；可执行动作 {exe} 条；输出目录 {out}")
    for w in rep.warnings:
        print("警告：", w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
