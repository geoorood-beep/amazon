#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml
from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "config" / "project_scope.json"
RULES_PATH = ROOT / "new_product_module" / "config" / "category_rules.example.yaml"
HISTORY_MANIFEST_PATH = ROOT / "history" / "v1.4-pre-8layer" / "MANIFEST.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    errors: list[str] = []
    scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    rules = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))

    _check_current_version(scope, rules, errors)
    _check_status_boundaries(rules, errors)
    _check_threshold_source(rules, errors)
    _check_threshold_profiles(rules, errors)
    _check_stage_ranges(rules, errors)
    _check_agent_directory(scope, errors)
    _check_eight_layer_structure(scope, errors)
    _check_single_source_separation(scope, errors)
    _check_managed_tree_registry(scope, errors)
    _check_markdown_targets(scope, errors)
    _check_threshold_manifest(rules, errors)
    _check_history_snapshot(errors)
    _check_fixed_workbooks(scope, errors)
    _check_v2_source(scope, errors)

    if errors:
        print("V2.0 一致性校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "V2.0 一致性校验通过：当前版本、Rug 边界、来源校验值、连续阈值摘要、"
        "阶段区间、两层 TEST_ONLY/HUMAN_EXEC 安全门和固定工作簿结构均有效。"
    )
    return 0


def _check_current_version(scope: dict, rules: dict, errors: list[str]) -> None:
    if scope.get("ruleset_version") != "V2.0":
        errors.append(
            f"config/project_scope.json.ruleset_version 必须为 V2.0，实际为 {scope.get('ruleset_version')}"
        )
    machine_version = str(rules.get("version") or "").lower()
    if "v2.0" not in machine_version:
        errors.append(f"派生 TEST_ONLY 配置版本必须标记 v2.0，实际为 {rules.get('version')}")
    if scope.get("runtime_version") != "V2.1":
        errors.append(
            f"config/project_scope.json.runtime_version 必须为 V2.1，实际为 {scope.get('runtime_version')}"
        )
    console = scope.get("operator_console", {})
    if console.get("version") != "V1.8":
        errors.append(f"运营网页版本必须为 V1.8，实际为 {console.get('version')}")


def _check_status_boundaries(rules: dict, errors: list[str]) -> None:
    expected = {
        "execution_mode": "HUMAN_EXECUTION_ONLY",
        "machine_rule_status": "TEST_ONLY",
        "stop_line_status": "BLOCKED_PENDING_THRESHOLD_ID",
    }
    for field, value in expected.items():
        if rules.get(field) != value:
            errors.append(f"{field} 必须为 {value}，实际为 {rules.get(field)}")

    ai_ads_readme = (ROOT / "ai_ads" / "README.md").read_text(encoding="utf-8")
    if "`TEST_ONLY`" not in ai_ads_readme:
        errors.append("ai_ads/README.md 未声明 TEST_ONLY")
    validator_text = (ROOT / "ai_ads" / "validator.py").read_text(encoding="utf-8")
    if "CAPABILITY_NOT_ACTIVE" not in validator_text:
        errors.append("SP_COLD_START 缺少 CAPABILITY_NOT_ACTIVE 阻断")
    if "PRODUCTION_EXECUTION_ENABLED = False" not in validator_text:
        errors.append("当前 HUMAN_EXECUTION_ONLY 版本缺少不可覆盖的生产执行保险")

    rank_bands = rules.get("strategy_rules", {}).get("ad_group_rank_bands", {})
    expected_rank_bands = {
        "single_keyword_max_rank": 30000,
        "multi_keyword_max_rank": 100000,
        "max_keywords_per_group": 5,
    }
    if rank_bands != expected_rank_bands:
        errors.append(
            "strategy_rules.ad_group_rank_bands 必须与已确认新品广告组分组阈值一致"
        )

    classifier_text = (ROOT / "new_product_module/src/rug_size_classifier.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("_RUNNER_SIZES", "_DOORMAT_SIZES", "_AREA_SIZES"):
        if forbidden in classifier_text:
            errors.append(f"尺寸阈值仍在运行代码中维护双真源：{forbidden}")

    architecture_text = (ROOT / "new_product_module/src/architecture_builder.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("aba_rank <= 30_000", "aba_rank <= 100_000"):
        if forbidden in architecture_text:
            errors.append(f"ABA 分组阈值仍硬编码在运行代码：{forbidden}")

    strategy_text = (ROOT / "new_product_module/src/strategy_mapper.py").read_text(
        encoding="utf-8"
    )
    if 'get("phrase_priority_aba_rank", 50000)' in strategy_text:
        errors.append("Phrase/Broad ABA 阈值仍以代码默认值回退")
    strategy_rules = rules.get("strategy_rules", {})
    if "phrase_priority_aba_rank" in strategy_rules:
        errors.append("Phrase/Broad 仍使用单一ABA排名分界")
    match_routing = strategy_rules.get("match_type_routing", {})
    expected_volume_bands = {
        "no_standalone_lt": 3000,
        "conditional_group_lt": 10000,
        "broad_test_lt": 30000,
        "phrase_priority_lt": 100000,
    }
    expected_concentration = {
        "sparse_query_phrase_max": 3,
        "mixed_top3_share_gte": 0.35,
        "phrase_top3_share_gte": 0.60,
    }
    if match_routing.get("root_monthly_volume_bands") != expected_volume_bands:
        errors.append("Phrase/Broad 词根月搜索量分层与阈值正文不一致")
    if match_routing.get("root_concentration") != expected_concentration:
        errors.append("Phrase/Broad 词根集中度门与阈值正文不一致")
    if match_routing.get("eligible_relevance_levels") != ["HIGH", "MEDIUM"]:
        errors.append("Phrase/Broad 相关性资格门必须仅允许 HIGH/MEDIUM")


def _check_threshold_source(rules: dict, errors: list[str]) -> None:
    relative = rules.get("threshold_source")
    expected = rules.get("threshold_source_sha256")
    if not relative or not expected:
        errors.append("规则配置缺少 threshold_source 或 threshold_source_sha256")
        return
    path = ROOT / relative
    if not path.is_file():
        errors.append(f"阈值确认原件不存在：{relative}")
        return
    actual = sha256(path)
    if actual != expected:
        errors.append(f"阈值确认原件 SHA-256 不一致：expected={expected}, actual={actual}")


def _check_threshold_profiles(rules: dict, errors: list[str]) -> None:
    profiles = rules.get("rug_analysis_thresholds", {})
    expected_cpa_upper = {"doormat": 13, "runner": 13, "area_small": 22, "area_large": 24}
    for profile, cpa_upper in expected_cpa_upper.items():
        values = profiles.get(profile)
        if not isinstance(values, dict):
            errors.append(f"缺少 Rug 阈值摘要：{profile}")
            continue
        for metric in ("cvr", "acos", "cpa"):
            parts = [part.strip() for part in str(values.get(metric) or "").split("|")]
            if len(parts) != 4 or any(not part for part in parts):
                errors.append(f"{profile}.{metric} 必须包含四个非空连续档位摘要")
        if values.get("cpa_normal_upper") != cpa_upper:
            errors.append(
                f"{profile}.cpa_normal_upper 应为 {cpa_upper}，实际为 {values.get('cpa_normal_upper')}"
            )

    round_profile = profiles.get("round", {})
    for metric in ("cvr", "acos", "cpa", "cpa_normal_upper"):
        if round_profile.get(metric) is not None:
            errors.append(f"圆形 Rug 未确认，round.{metric} 必须保持 null")


def _check_stage_ranges(rules: dict, errors: list[str]) -> None:
    stages = rules.get("order_stage_aba_table", [])
    previous_max = None
    for index, stage in enumerate(stages):
        lower = stage.get("min_daily_orders")
        upper = stage.get("max_daily_orders")
        if lower is None:
            errors.append(f"阶段 {stage.get('stage')} 缺少 min_daily_orders")
            continue
        if index == 0 and lower != 0:
            errors.append("订单阶段必须从 0 开始")
        if previous_max is not None and lower != previous_max:
            errors.append(
                f"订单阶段存在空档或重叠：上一上限 {previous_max}，{stage.get('stage')} 下限 {lower}"
            )
        if upper is not None and upper <= lower:
            errors.append(f"阶段 {stage.get('stage')} 的上限必须大于下限")
        previous_max = upper
    if stages and stages[-1].get("max_daily_orders") is not None:
        errors.append("最后一个订单阶段必须无上限")


def _check_agent_directory(scope: dict, errors: list[str]) -> None:
    directory_text = (ROOT / "agents" / "agents-directory.md").read_text(encoding="utf-8")
    if scope.get("ruleset_version") not in directory_text:
        errors.append(
            f"agents-directory.md 未展示当前版本：{scope.get('ruleset_version')}"
        )
    for heading in ("具体规则", "具体阈值", "数据源", "输出/字段合同"):
        if heading not in directory_text:
            errors.append(f"agents-directory.md 缺少可维护导航列：{heading}")

    click_targets = re.findall(
        r"(?<!!)\[[^\]]+\]\((?:<([^>]+)>|([^\s)]+))\)", directory_text
    )
    normalized_targets = {left or right for left, right in click_targets}
    for target in sorted(normalized_targets):
        if target.endswith(("/README.md", "/metadata.md")):
            errors.append(f"agents-directory.md 仍指向目录中转页：{target}")

    required_terminal_targets = {
        str(ROOT / "rules/domains/new-product/attribute-and-selection.md"),
        str(ROOT / "rules/domains/old-product/diagnosis.md"),
        str(ROOT / "rules/domains/search-term/semantic-aggregation.md"),
        str(ROOT / "thresholds/rug/performance.md"),
        str(ROOT / "thresholds/rug/new-product-stage.md"),
        str(ROOT / "reference/rug-aba/area_rug_ABA关键词库_202605_v8.xlsx"),
        str(
            ROOT
            / "reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx"
        ),
        str(ROOT / "contracts/data-input.md"),
    }
    for target in sorted(required_terminal_targets - normalized_targets):
        errors.append(f"agents-directory.md 缺少具体信息直达链接：{target}")

    for relative in scope.get("compatibility_agent_paths", []):
        if relative == "agents/agents-directory.md":
            continue
        label = Path(relative).name
        if label not in directory_text:
            errors.append(f"agents-directory.md 未登记：{label}")


def _check_eight_layer_structure(scope: dict, errors: list[str]) -> None:
    expected_layers = {
        f"architecture/layers/{number:02d}-{slug}.md"
        for number, slug in (
            (1, "react-router"),
            (2, "plan-execute"),
            (3, "domain-agents"),
            (4, "reflective-validator"),
            (5, "tool-augmented"),
            (6, "memory-state"),
            (7, "rag-knowledge"),
            (8, "autonomous-loop"),
        )
    }
    configured_layers = {
        path
        for path in scope.get("required_architecture_paths", [])
        if path.startswith("architecture/layers/")
    }
    if configured_layers != expected_layers:
        errors.append("八层架构文件集合不完整或出现额外层")

    architecture_text = (ROOT / "architecture" / "README.md").read_text(encoding="utf-8")
    directory_text = (ROOT / "agents" / "agents-directory.md").read_text(encoding="utf-8")
    for number in range(1, 9):
        token = f"{number:02d}"
        if token not in architecture_text:
            errors.append(f"architecture/README.md 未登记第 {token} 层")
        if token not in directory_text:
            errors.append(f"agents-directory.md 未展示第 {token} 层")


def _check_single_source_separation(scope: dict, errors: list[str]) -> None:
    compatibility_map = scope.get("legacy_compatibility_map", {})
    for legacy, canonical in compatibility_map.items():
        path = ROOT / legacy
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "兼容入口" not in text:
            errors.append(f"旧路径未标记为兼容入口：{legacy}")
        if "不再维护" not in text and "不维护" not in text:
            errors.append(f"兼容入口未声明停止维护正文：{legacy}")
        if canonical not in text:
            errors.append(f"兼容入口缺少当前真源路由：{legacy} -> {canonical}")
        if len(text.splitlines()) > 40:
            errors.append(f"兼容入口过长，可能重新堆入规则：{legacy}")

    quantitative_patterns = {
        "百分比阈值": re.compile(r"\d+(?:\.\d+)?\s*%"),
        "货币阈值": re.compile(r"\$\s*\d"),
        "低样本数值": re.compile(r"O\s*[<>=]\s*\d"),
        "ABA 排名比较值": re.compile(r"ABA[^\n]{0,40}(?:<=|>=|<|>)\s*[\d,]+", re.IGNORECASE),
    }
    active_rule_paths = [ROOT / "AGENTS.md"] + [
        ROOT / relative for relative in scope.get("required_rule_paths", [])
    ]
    for path in active_rule_paths:
        text = path.read_text(encoding="utf-8")
        for label, pattern in quantitative_patterns.items():
            if pattern.search(text):
                errors.append(
                    f"{path.relative_to(ROOT)} 含{label}；数值应移入 thresholds/ 并只引用 Threshold ID"
                )

    old_threshold_text = (ROOT / "agents" / "category data thresholds.md").read_text(
        encoding="utf-8"
    )
    for label, pattern in quantitative_patterns.items():
        if pattern.search(old_threshold_text):
            errors.append(f"旧阈值兼容入口含{label}，存在双真源风险")


def _check_managed_tree_registry(scope: dict, errors: list[str]) -> None:
    groups = {
        "architecture": "required_architecture_paths",
        "rules": "required_rule_paths",
        "thresholds": "required_threshold_paths",
        "contracts": "required_contract_paths",
        "knowledge": "required_knowledge_paths",
    }
    for directory, group in groups.items():
        discovered = {
            str(path.relative_to(ROOT))
            for path in (ROOT / directory).rglob("*.md")
            if path.is_file()
        }
        configured = set(scope.get(group, []))
        if discovered != configured:
            missing = sorted(discovered - configured)
            stale = sorted(configured - discovered)
            errors.append(
                f"{directory}/ 文件登记不一致：未登记={missing}，无效登记={stale}"
            )


def _check_markdown_targets(scope: dict, errors: list[str]) -> None:
    active_paths = {
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "reference" / "rug-aba" / "metadata.md",
        ROOT / "reference" / "category-history" / "rug" / "metadata.md",
        *[ROOT / path for path in scope.get("compatibility_agent_paths", [])],
        *[ROOT / path for path in scope.get("required_architecture_paths", [])],
        *[ROOT / path for path in scope.get("required_rule_paths", [])],
        *[ROOT / path for path in scope.get("required_threshold_paths", [])],
        *[ROOT / path for path in scope.get("required_contract_paths", [])],
        *[ROOT / path for path in scope.get("required_knowledge_paths", [])],
    }
    root_prefixes = {
        "agents",
        "architecture",
        "contracts",
        "docs",
        "history",
        "knowledge",
        "reference",
        "rules",
        "thresholds",
    }
    code_route_pattern = re.compile(r"`([^`]+\.md)`")
    markdown_link_pattern = re.compile(
        r"(?<!!)\[[^\]]+\]\((<[^>]+>|[^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)"
    )
    reported: set[tuple[Path, str]] = set()
    for path in sorted(active_paths):
        text = path.read_text(encoding="utf-8")
        for token in code_route_pattern.findall(text):
            if any(marker in token for marker in ("*", "<", ">")):
                continue
            candidate = Path(token)
            if candidate.is_absolute():
                continue
            if candidate.parts and candidate.parts[0] in root_prefixes:
                target = ROOT / candidate
            else:
                target = path.parent / candidate
            if not target.is_file() and (path, token) not in reported:
                errors.append(
                    f"Markdown 路由不存在：{path.relative_to(ROOT)} -> {token}"
                )
                reported.add((path, token))

        for raw_token in markdown_link_pattern.findall(text):
            token = raw_token.strip()
            if token.startswith("<") and token.endswith(">"):
                token = token[1:-1]
            token = token.split("#", 1)[0].split("?", 1)[0]
            if not token or token.startswith(("http://", "https://", "mailto:")):
                continue
            if any(marker in token for marker in ("*", "{", "}")):
                continue
            target = Path(token) if token.startswith("/") else path.parent / token
            if not target.exists() and (path, raw_token) not in reported:
                errors.append(
                    f"Markdown 点击链接不存在：{path.relative_to(ROOT)} -> {raw_token}"
                )
                reported.add((path, raw_token))


def _check_threshold_manifest(rules: dict, errors: list[str]) -> None:
    manifest_path = ROOT / "thresholds" / "rug" / "source-manifest.md"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    expected_source = str(rules.get("threshold_source") or "")
    expected_hash = str(rules.get("threshold_source_sha256") or "")
    for token, label in (
        (expected_source, "阈值原件路径"),
        (expected_hash, "阈值原件 SHA-256"),
        ("HUMAN_EXECUTION_ONLY", "人工执行状态"),
        ("TEST_ONLY", "机器状态"),
    ):
        if not token or token not in manifest_text:
            errors.append(f"thresholds/rug/source-manifest.md 缺少{label}")

    derived = scope_from_disk().get("derived_machine_config", {})
    if derived.get("path") != str(RULES_PATH.relative_to(ROOT)):
        errors.append("派生 TEST_ONLY 配置路径与当前校验器不一致")


def scope_from_disk() -> dict:
    return json.loads(SCOPE_PATH.read_text(encoding="utf-8"))


def _check_history_snapshot(errors: list[str]) -> None:
    if not HISTORY_MANIFEST_PATH.is_file():
        errors.append("缺少八层拆分前历史 manifest")
        return
    manifest_text = HISTORY_MANIFEST_PATH.read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", manifest_text, flags=re.MULTILINE)
    if not rows:
        errors.append("历史 manifest 未解析到文件校验值")
        return
    snapshot_root = HISTORY_MANIFEST_PATH.parent
    for relative, expected_hash in rows:
        path = snapshot_root / relative
        if not path.is_file():
            errors.append(f"历史快照缺少文件：{path.relative_to(ROOT)}")
            continue
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            errors.append(
                f"历史快照被改动：{path.relative_to(ROOT)} expected={expected_hash}, actual={actual_hash}"
            )


def _check_fixed_workbooks(scope: dict, errors: list[str]) -> None:
    aba_dir = ROOT / scope["category_data_map"]["rug"]["aba"]
    files = sorted(aba_dir.glob("*.xlsx"))
    expected_names = {
        "area_rug_ABA关键词库_202605_v8.xlsx",
        "bathroom_rugs_ABA关键词库_202605.xlsx",
        "kitchen_rugs_ABA关键词库_202605_v2.xlsx",
        "outdoor_rug_ABA关键词库_202605_v2.xlsx",
    }
    if {path.name for path in files} != expected_names:
        errors.append("Rug ABA 固定目录中的工作簿集合与项目合同不一致")
    required_headers = {"搜索词", "搜索量排名", "地毯类型", "推荐层级", "合规状态", "广告状态"}
    for path in files:
        workbook = load_workbook(path, read_only=True, data_only=True)
        if "广告词库" not in workbook.sheetnames:
            errors.append(f"{path.name} 缺少广告词库 sheet")
            continue
        headers = {str(cell.value or "").strip() for cell in workbook["广告词库"][1]}
        missing = required_headers.difference(headers)
        if missing:
            errors.append(f"{path.name}/广告词库 缺字段：{sorted(missing)}")

    history = ROOT / "reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx"
    workbook = load_workbook(history, read_only=True, data_only=True)
    if "term_summary" not in workbook.sheetnames:
        errors.append("Rug 历史效果词工作簿缺少 term_summary")


def _check_v2_source(scope: dict, errors: list[str]) -> None:
    source = scope.get("architecture_source", {})
    path = ROOT / source.get("path", "")
    expected = source.get("sha256")
    if not path.is_file():
        errors.append("V2 架构来源文件不存在")
    elif sha256(path) != expected:
        errors.append("V2 架构来源文件 SHA-256 与项目合同不一致")


if __name__ == "__main__":
    sys.exit(main())
