#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "docs/v2/phase1-rule-decisions.yaml"
SCOPE_PATH = ROOT / "config/project_scope.json"
EXPECTED_ISSUES = {f"L-{number:03d}" for number in range(1, 12)}
ALLOWED_STATUSES = {
    "DRAFT_REVIEW_ONLY",
    "CONFIRMED_RULE",
    "TESTED_ACTIVE",
    "DEPRECATED",
}
REQUIRED_DECISION_FIELDS = {"issue_id", "title", "status", "decision"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    with REGISTRY_PATH.open(encoding="utf-8") as source:
        payload = yaml.safe_load(source)

    registry = payload["registry"]
    current_version = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))["ruleset_version"]
    if registry.get("active_document_version") != current_version:
        raise ValueError(
            "裁决登记表当前文档版本与项目版本不一致: "
            f"registry={registry.get('active_document_version')}, project={current_version}"
        )
    if registry["status"] != "DRAFT_REVIEW_ONLY":
        raise ValueError("机器规则包未激活前，裁决登记表必须保持 DRAFT_REVIEW_ONLY")

    source_paths = set()
    for source in payload["sources"]:
        path = ROOT / source["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256(path) != source["sha256"]:
            raise ValueError(f"来源文件哈希不匹配: {path}")
        source_paths.add(source["path"])

    if len(source_paths) != len(payload["sources"]):
        raise ValueError("来源文件路径重复")

    decisions = payload["decisions"]
    issue_ids = set()
    for decision in decisions:
        missing = REQUIRED_DECISION_FIELDS - decision.keys()
        if missing:
            raise ValueError(f"{decision.get('issue_id', 'UNKNOWN')} 缺字段: {sorted(missing)}")
        if decision["status"] not in ALLOWED_STATUSES:
            raise ValueError(f"{decision['issue_id']} 状态非法: {decision['status']}")
        issue_ids.add(decision["issue_id"])

    if issue_ids != EXPECTED_ISSUES:
        missing = sorted(EXPECTED_ISSUES - issue_ids)
        extra = sorted(issue_ids - EXPECTED_ISSUES)
        raise ValueError(f"裁决编号不完整，缺少={missing}，多出={extra}")
    if len(decisions) != len(issue_ids):
        raise ValueError("存在重复裁决编号")

    non_confirmed = [
        decision["issue_id"]
        for decision in decisions
        if decision["status"] != "CONFIRMED_RULE"
    ]
    if non_confirmed:
        raise ValueError(f"V2.0 人工规则仍有未确认裁决: {non_confirmed}")

    active_drafts = [
        decision["issue_id"]
        for decision in decisions
        if decision["status"] == "DRAFT_REVIEW_ONLY"
        and decision.get("active", False)
    ]
    if active_drafts:
        raise ValueError(f"草案不得激活: {active_drafts}")

    threshold_inputs = payload.get("confirmed_threshold_inputs", [])
    if not threshold_inputs:
        raise ValueError("缺少人工阈值回填登记")

    threshold_301 = next(
        (
            item
            for item in threshold_inputs
            if item.get("threshold_id") == "THR-301"
        ),
        None,
    )
    if not threshold_301 or threshold_301.get("value") != 7:
        raise ValueError("THR-301 未登记为 7 个自然日")

    print(
        "第一阶段裁决登记表校验通过："
        f"{len(decisions)}项裁决、{len(payload['sources'])}份来源，"
        f"当前文档版本 {current_version}，人工规则已确认，机器包未激活。"
    )


if __name__ == "__main__":
    main()
