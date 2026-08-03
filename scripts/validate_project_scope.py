#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "config" / "project_scope.json"
WEEKLY_CONFIG_PATH = ROOT / "config" / "weekly_amazon_report_ingest.json"
REQUIRED_PATH_GROUPS = {
    "compatibility_agent_paths": "兼容 AGENT",
    "required_architecture_paths": "八层架构文件",
    "required_integration_paths": "第05层外部接入预留文件",
    "required_rule_paths": "当前规则文件",
    "required_threshold_paths": "当前阈值文件",
    "required_contract_paths": "数据合同文件",
    "required_knowledge_paths": "知识源文件",
    "required_history_paths": "历史快照文件",
    "required_runtime_paths": "项目运行或校验文件",
    "required_release_paths": "V2.0冻结发布文件",
}


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    errors: list[str] = []

    if not SCOPE_PATH.is_file():
        print(f"缺少项目边界配置：{SCOPE_PATH}")
        return 1

    scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    project_name = scope.get("project_name")
    ruleset_version = scope.get("ruleset_version")
    allowed_categories = scope.get("allowed_categories", [])

    if ruleset_version != "V2.0":
        errors.append(f"当前规则版本必须为 V2.0，实际为 {ruleset_version}")

    for group, label in REQUIRED_PATH_GROUPS.items():
        paths = scope.get(group)
        if not isinstance(paths, list) or not paths:
            errors.append(f"项目边界配置缺少非空列表：{group}")
            continue
        for relative in paths:
            if not (ROOT / relative).is_file():
                errors.append(f"缺少{label}：{relative}")

    for relative in scope.get("required_reference_paths", []):
        if not (ROOT / relative).exists():
            errors.append(f"缺少本项目固定数据：{relative}")

    for relative in scope.get("forbidden_reference_paths", []):
        if (ROOT / relative).exists():
            errors.append(f"发现禁止的跨项目数据：{relative}")

    forbidden_tokens = tuple(scope.get("forbidden_reference_paths", []))
    for path in (ROOT / "agents").glob("*"):
        if path.suffix.lower() not in {".md", ".html"}:
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                errors.append(f"{path.relative_to(ROOT)} 仍引用禁止数据路径：{token}")

    compatibility_map = scope.get("legacy_compatibility_map", {})
    expected_compatibility = set(scope.get("compatibility_agent_paths", [])) - {
        "agents/agents-directory.md"
    }
    if set(compatibility_map) != expected_compatibility:
        errors.append("旧 AGENT 兼容映射与 compatibility_agent_paths 不一致")
    for legacy, canonical in compatibility_map.items():
        legacy_path = ROOT / legacy
        canonical_path = ROOT / canonical
        if not canonical_path.is_file():
            errors.append(f"兼容映射指向不存在的当前真源：{legacy} -> {canonical}")
        if legacy_path.is_file():
            legacy_text = legacy_path.read_text(encoding="utf-8")
            if canonical not in legacy_text:
                errors.append(f"兼容入口未路由到当前真源：{legacy} -> {canonical}")

    single_source = scope.get("human_single_source", {})
    expected_sources = {"architecture", "rules", "thresholds", "contracts", "knowledge", "history"}
    if set(single_source) != expected_sources:
        errors.append("human_single_source 必须完整登记六类真源")
    for source_type, relative in single_source.items():
        if not (ROOT / relative).is_file():
            errors.append(f"{source_type} 真源不存在：{relative}")

    derived = scope.get("derived_machine_config", {})
    if derived.get("status") != "TEST_ONLY":
        errors.append("派生机器配置必须保持 TEST_ONLY")
    if derived.get("maintenance_source") != single_source.get("thresholds"):
        errors.append("派生机器配置必须指向阈值人工真源")
    derived_path = ROOT / derived.get("path", "")
    if not derived_path.is_file():
        errors.append(f"派生机器配置不存在：{derived.get('path')}")

    integration = scope.get("integration_gateway", {})
    if integration.get("status") != "PLACEHOLDER_NOT_ACTIVE":
        errors.append("第05层外部接入网关必须保持 PLACEHOLDER_NOT_ACTIVE")
    if integration.get("receive_only") is not True:
        errors.append("第05层外部接入网关必须保持 receive_only")
    if integration.get("action_execution_enabled") is not False:
        errors.append("第05层外部接入网关不得启用广告动作执行")
    for key in ("path", "config_template", "contract"):
        relative = integration.get(key)
        if not relative or not (ROOT / relative).is_file():
            errors.append(f"第05层外部接入网关缺少有效 {key}：{relative}")

    architecture = scope.get("architecture_source", {})
    architecture_path = ROOT / architecture.get("path", "")
    expected_sha256 = architecture.get("sha256")
    if not architecture_path.is_file():
        errors.append(f"缺少 V2 架构来源：{architecture.get('path')}")
    elif expected_sha256:
        actual_sha256 = hashlib.sha256(architecture_path.read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            errors.append(
                f"V2 架构来源校验值不一致：expected={expected_sha256}, actual={actual_sha256}"
            )

    for relative in ("AGENTS.md", "README.md", "VERSION.md", "docs/项目数据映射.md"):
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"缺少项目文件：{relative}")
            continue
        text = path.read_text(encoding="utf-8")
        if project_name not in text:
            errors.append(f"{relative} 未写入项目名称：{project_name}")
        if ruleset_version not in text:
            errors.append(f"{relative} 未写入当前版本：{ruleset_version}")

    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for category in allowed_categories:
        if category not in agents_text:
            errors.append(f"AGENTS.md 未声明允许类目：{category}")

    if not WEEKLY_CONFIG_PATH.is_file():
        errors.append("缺少周报配置：config/weekly_amazon_report_ingest.json")
    else:
        weekly = json.loads(WEEKLY_CONFIG_PATH.read_text(encoding="utf-8"))
        configured_paths = [
            weekly.get("output", {}).get("save_root"),
            weekly.get("analysis", {}).get("output_root"),
        ]
        for value in configured_paths:
            if not value:
                errors.append("周报配置缺少保存路径")
                continue
            target = Path(value).expanduser()
            if not target.is_absolute():
                target = ROOT / target
            if not is_within(target, ROOT):
                errors.append(f"周报保存路径越过项目边界：{target}")

    for path in ROOT.rglob("*"):
        relative_parts = path.relative_to(ROOT).parts
        if relative_parts and relative_parts[0] == ".venv":
            continue
        if path.is_symlink() and not is_within(path.resolve(), ROOT):
            errors.append(f"发现指向项目外的符号链接：{path.relative_to(ROOT)} -> {path.resolve()}")

    if errors:
        print(f"{project_name} 项目边界校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    category_text = ", ".join(allowed_categories)
    print(
        f"{project_name} 项目边界校验通过："
        f"当前版本 {ruleset_version}，允许类目 [{category_text}]，"
        "固定数据、禁止路径和周报输出路径均符合配置。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
