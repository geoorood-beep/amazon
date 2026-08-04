from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ARCHITECTURE_LAYERS = [
    "architecture/layers/01-react-router.md",
    "architecture/layers/02-plan-execute.md",
    "architecture/layers/03-domain-agents.md",
    "architecture/layers/04-reflective-validator.md",
    "architecture/layers/05-tool-augmented.md",
    "architecture/layers/06-memory-state.md",
    "architecture/layers/07-rag-knowledge.md",
    "architecture/layers/08-autonomous-loop.md",
]
GLOBAL_RUNTIME_SOURCES = [
    "operator_console/backend/agents_context.py",
    "operator_console/backend/validator.py",
    "operator_console/contracts/operator-result.schema.json",
]
IGNORED_NAMES = {".DS_Store"}


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@lru_cache(maxsize=4096)
def _sha256_file_cached(raw_path: str, size: int, mtime_ns: int, ctime_ns: int) -> str:
    path = Path(raw_path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_file(path: Path) -> str:
    stat = path.stat()
    return _sha256_file_cached(str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def _directory_files(path: Path) -> list[Path]:
    return sorted(
        item
        for item in path.rglob("*")
        if item.is_file()
        and item.name not in IGNORED_NAMES
        and not item.name.startswith(("._", "~$"))
    )


def _sha256_directory(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    files = _directory_files(path)
    for item in files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        file_digest = _sha256_file(item).encode("ascii")
        digest.update(file_digest)
    return digest.hexdigest(), len(files)


def source_record(root: Path, raw_path: str, role: str, *, external: bool = False) -> dict[str, Any]:
    candidate = Path(raw_path).expanduser()
    path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if not external and path != root and root not in path.parents:
        return {
            "role": role,
            "path": raw_path,
            "status": "OUT_OF_SCOPE",
            "source_type": "missing",
            "file_count": 0,
            "sha256": None,
        }
    display_path = str(path) if external else path.relative_to(root).as_posix()
    if path.is_dir():
        digest, file_count = _sha256_directory(path)
        source_type = "directory"
    elif path.is_file():
        digest = _sha256_file(path)
        file_count = 1
        source_type = "file"
    else:
        digest = None
        file_count = 0
        source_type = "missing"
    return {
        "role": role,
        "path": display_path,
        "status": "AVAILABLE" if path.exists() else "MISSING",
        "source_type": source_type,
        "file_count": file_count,
        "sha256": digest,
    }


def _unique(values: list[str | None]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def trusted_intent_route(root: Path, intent: str) -> dict[str, Any] | None:
    try:
        payload = json.loads((root / "config/operator_intents.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    route = payload.get("intents", {}).get(intent)
    return route if isinstance(route, dict) else None


def build_tool_receipt(
    root: Path,
    request: dict[str, Any],
    preprocessing: dict[str, Any],
) -> dict[str, Any]:
    intent = str(request.get("intent") or "")
    route = trusted_intent_route(root, intent) or {}
    inputs: list[dict[str, Any]] = []
    for raw in preprocessing.get("input_artifacts", []):
        inputs.append(source_record(root, str(raw), "tool_input", external=Path(str(raw)).is_absolute()))
    report_source = str(request.get("fields", {}).get("report_source_path") or "").strip()
    if report_source and report_source not in {item["path"] for item in inputs}:
        inputs.append(source_record(root, report_source, "tool_input", external=True))
    inputs.extend(
        source_record(root, path, "tool_knowledge_input")
        for path in _unique(list(route.get("knowledge_entries") or []))
    )
    outputs = [
        source_record(root, str(raw), "tool_output", external=Path(str(raw)).is_absolute())
        for raw in preprocessing.get("artifacts", [])
    ]
    configs = [
        source_record(root, path, "tool_config")
        for path in _unique(list(route.get("config_entries") or []))
    ]
    tools = [
        source_record(root, path, "tool_implementation")
        for path in _unique(list(route.get("tool_entries") or []))
    ]
    payload = {
        "schema_version": "1.0",
        "job_id": request.get("job_id"),
        "intent": intent,
        "tool_id": route.get("preprocessor"),
        "status": preprocessing.get("status"),
        "inputs": inputs,
        "configs": configs,
        "tools": tools,
        "outputs": outputs,
    }
    payload["receipt_id"] = canonical_digest(payload)
    return payload


def verify_tool_receipts(
    root: Path,
    request: dict[str, Any],
    preprocessing: dict[str, Any],
) -> list[str]:
    receipts = preprocessing.get("tool_receipts")
    if not isinstance(receipts, list) or len(receipts) != 1:
        return ["TOOL_RECEIPT_MISSING"]
    expected = build_tool_receipt(root, request, preprocessing)
    return [] if receipts[0] == expected else ["TOOL_RECEIPT_MISMATCH"]


def build_agents_analysis_context(
    root: Path,
    request: dict[str, Any],
    preprocessing: dict[str, Any],
) -> dict[str, Any]:
    """Compile the server-trusted V2.1 execution context.

    The request copy of routing is never trusted as project truth. The compiler
    reloads the intent route, all eight architecture layers and every source
    digest from the current checkout. There are no permissive fallback routes.
    """

    intent = str(request.get("intent") or "")
    route = trusted_intent_route(root, intent)
    submitted_route = request.get("routing")
    route_matches = isinstance(route, dict) and submitted_route == route
    route = route or {}

    root_sources = [
        source_record(root, "AGENTS.md", "agents_root"),
        source_record(root, "config/project_scope.json", "project_scope"),
        source_record(root, "config/operator_intents.json", "intent_router"),
        *[source_record(root, path, "runtime_guard") for path in GLOBAL_RUNTIME_SOURCES],
    ]
    architecture = [source_record(root, path, "architecture_layer") for path in ARCHITECTURE_LAYERS]
    rules = [source_record(root, path, "rule") for path in _unique(list(route.get("rule_entries") or []))]
    thresholds = [
        source_record(root, path, "threshold")
        for path in _unique(list(route.get("threshold_entries") or []))
    ]
    knowledge = [
        source_record(root, path, "knowledge")
        for path in _unique(list(route.get("knowledge_entries") or []))
    ]
    tools = [source_record(root, path, "tool") for path in _unique(list(route.get("tool_entries") or []))]
    configs = [
        source_record(root, path, "config")
        for path in _unique(list(route.get("config_entries") or []))
    ]
    contract_paths = list(route.get("input_contracts") or [])
    if route.get("output_contract"):
        contract_paths.append(route["output_contract"])
    contracts = [source_record(root, path, "contract") for path in _unique(contract_paths)]

    evidence: list[dict[str, Any]] = []
    report_source = str(request.get("fields", {}).get("report_source_path") or "").strip()
    if report_source:
        evidence.append(source_record(root, report_source, "uploaded_reports", external=True))
    for raw in preprocessing.get("input_artifacts", []):
        evidence.append(source_record(root, str(raw), "preprocessor_input", external=True))
    for raw in preprocessing.get("artifacts", []):
        evidence.append(source_record(root, str(raw), "preprocessed_evidence", external=True))

    groups = {
        "root": root_sources,
        "architecture": architecture,
        "rules": rules,
        "thresholds": thresholds,
        "knowledge": knowledge,
        "tools": tools,
        "configs": configs,
        "contracts": contracts,
        "evidence": evidence,
    }
    all_sources = [item for group in groups.values() for item in group]
    missing = [item["path"] for item in all_sources if item["status"] != "AVAILABLE"]
    layer_count = sum(item["status"] == "AVAILABLE" for item in architecture)
    receipt_errors = (
        verify_tool_receipts(root, request, preprocessing)
        if preprocessing.get("status") == "READY_FOR_ANALYSIS"
        else []
    )
    required_codex_sources = [
        item["path"]
        for group_name in ("root", "architecture", "rules", "thresholds", "knowledge", "tools", "configs", "contracts")
        for item in groups[group_name]
    ]
    context: dict[str, Any] = {
        "schema_version": "2.1",
        "ruleset_version": "V2.0",
        "runtime_version": "V2.1",
        "agents_entry": "AGENTS.md",
        "project_scope": "config/project_scope.json",
        "intent_router": "config/operator_intents.json",
        "intent": intent,
        "category": "rug",
        "execution_boundary": "HUMAN_EXECUTION_ONLY",
        "preprocessor": route.get("preprocessor"),
        "route_matches_server_truth": route_matches,
        "architecture_layer_coverage": {"available": layer_count, "required": 8},
        "sources": groups,
        "source_count": len(all_sources),
        "missing_sources": missing,
        "required_codex_sources": required_codex_sources,
        "tool_receipt_ids": [
            item.get("receipt_id")
            for item in preprocessing.get("tool_receipts", [])
            if isinstance(item, dict) and item.get("receipt_id")
        ],
        "route_status": "READY"
        if route_matches and not missing and layer_count == 8 and not receipt_errors
        else "BLOCKED",
        "blocking_codes": [
            *([] if route_matches else ["ROUTE_MISMATCH"]),
            *([] if layer_count == 8 else ["ARCHITECTURE_LAYER_MISSING"]),
            *(["SOURCE_MISSING"] if missing else []),
            *receipt_errors,
        ],
    }
    context["context_digest"] = canonical_digest(context)
    return context


def verify_agents_analysis_context(
    root: Path,
    request: dict[str, Any],
    preprocessing: dict[str, Any],
) -> list[str]:
    actual = preprocessing.get("agents_context")
    if not isinstance(actual, dict):
        return ["AGENTS_CONTEXT_MISSING"]
    expected = build_agents_analysis_context(root, request, preprocessing)
    errors: list[str] = []
    if actual.get("context_digest") != expected.get("context_digest"):
        errors.append("AGENTS_CONTEXT_DIGEST_MISMATCH")
    if actual != expected:
        errors.append("AGENTS_CONTEXT_CONTENT_MISMATCH")
    if expected.get("route_status") != "READY":
        errors.extend(str(code) for code in expected.get("blocking_codes", []))
    return list(dict.fromkeys(errors))
