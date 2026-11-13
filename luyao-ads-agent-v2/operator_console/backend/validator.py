from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents_context import (
    canonical_digest,
    source_record,
    verify_agents_analysis_context,
    verify_tool_receipts,
)


ROOT = Path(__file__).resolve().parents[2]
ALLOWED_INTENTS = {
    "NEW_PRODUCT_PROMOTION",
    "OLD_PRODUCT_OPTIMIZATION",
    "AGGREGATE_REPORTS",
    "WEEKLY_REVIEW",
}
ALLOWED_STATUSES = {
    "READY_FOR_HUMAN_REVIEW",
    "DATA_REQUIRED",
    "VALIDATOR_BLOCKED",
    "CODEX_UNAVAILABLE",
}


def _digest_without_id(receipt: dict[str, Any]) -> str:
    payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    return canonical_digest(payload)


def _registered_sources(context: dict[str, Any]) -> set[str]:
    return {
        str(item.get("path"))
        for group in (context.get("sources") or {}).values()
        for item in group
        if isinstance(item, dict) and item.get("status") == "AVAILABLE" and item.get("path")
    }


def _verify_codex_receipt(
    result: dict[str, Any],
    preprocessing: dict[str, Any],
) -> list[str]:
    receipt = preprocessing.get("codex_invocation_receipt")
    if not isinstance(receipt, dict):
        return ["CODEX_RECEIPT_MISSING"]
    errors: list[str] = []
    if receipt.get("receipt_id") != _digest_without_id(receipt):
        errors.append("CODEX_RECEIPT_DIGEST_MISMATCH")
    if receipt.get("status") != "SUCCESS" or receipt.get("codex_invoked") is not True:
        errors.append("CODEX_INVOCATION_NOT_SUCCESSFUL")
    provenance = result.get("provenance") or {}
    context = preprocessing.get("agents_context") or {}
    if receipt.get("codex_run_id") != provenance.get("codex_run_id"):
        errors.append("CODEX_RUN_ID_MISMATCH")
    if receipt.get("agents_context_digest") != context.get("context_digest"):
        errors.append("CODEX_CONTEXT_DIGEST_MISMATCH")
    output_path = Path(str(receipt.get("output_path") or ""))
    if not output_path.is_file():
        errors.append("CODEX_OUTPUT_MISSING")
    else:
        output_source = source_record(ROOT, str(output_path), "codex_output", external=True)
        if output_source.get("sha256") != receipt.get("output_sha256"):
            errors.append("CODEX_OUTPUT_SHA_MISMATCH")
        try:
            raw_result = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            errors.append("CODEX_OUTPUT_JSON_INVALID")
        else:
            current = {key: value for key, value in result.items() if key != "artifacts"}
            raw = {key: value for key, value in raw_result.items() if key != "artifacts"}
            if current != raw:
                errors.append("CODEX_RESULT_PAYLOAD_MISMATCH")
    return errors


def _verify_final_artifacts(result: dict[str, Any], preprocessing: dict[str, Any]) -> list[str]:
    artifacts = result.get("artifacts")
    receipts = preprocessing.get("final_artifact_receipts")
    if not isinstance(artifacts, list) or not artifacts:
        return ["FINAL_ARTIFACT_MISSING"]
    if not isinstance(receipts, list) or not receipts:
        return ["FINAL_ARTIFACT_RECEIPT_MISSING"]
    by_path = {str(item.get("path")): item for item in receipts if isinstance(item, dict)}
    errors: list[str] = []
    for raw in artifacts:
        path = Path(str(raw)).resolve()
        receipt = by_path.get(str(path))
        if not receipt:
            errors.append("FINAL_ARTIFACT_UNRECEIPTED")
            continue
        current = source_record(ROOT, str(path), "final_artifact", external=True)
        if current.get("status") != "AVAILABLE" or current.get("sha256") != receipt.get("sha256"):
            errors.append("FINAL_ARTIFACT_SHA_MISMATCH")
    if set(by_path) != {str(Path(str(item)).resolve()) for item in artifacts}:
        errors.append("FINAL_ARTIFACT_SET_MISMATCH")
    return list(dict.fromkeys(errors))


def validate_operator_result(
    result: dict[str, Any],
    request: dict[str, Any],
    preprocessing: dict[str, Any],
    *,
    require_final_artifacts: bool = False,
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def block(code: str, message: str) -> None:
        findings.append({"level": "BLOCK", "code": code, "message": message})

    if result.get("job_id") != request.get("job_id"):
        block("JOB_ID_MISMATCH", "Codex结果与任务ID不一致")
    if result.get("intent") != request.get("intent"):
        block("INTENT_MISMATCH", "Codex结果与任务意图不一致")
    if result.get("intent") not in ALLOWED_INTENTS:
        block("INTENT_NOT_ALLOWED", "结果包含未登记的任务意图")
    if result.get("category") != "rug":
        block("NON_RUG_RESULT", "结果不是Rug类目")
    if result.get("status") not in ALLOWED_STATUSES:
        block("RESULT_STATUS_INVALID", "结果状态不在允许枚举中")
    elif result.get("status") in {"DATA_REQUIRED", "VALIDATOR_BLOCKED", "CODEX_UNAVAILABLE"}:
        block("RESULT_NOT_READY", f"结果状态为 {result.get('status')}，不得标记任务完成")

    safety = result.get("safety")
    if not isinstance(safety, dict):
        block("SAFETY_MISSING", "结果缺少安全字段")
    else:
        if safety.get("execution_allowed") is not False:
            block("EXECUTION_PERMISSION_FORGED", "运营入口不得声明可执行")
        if safety.get("auto_apply") is not False:
            block("AUTO_APPLY_FORGED", "运营入口不得自动应用")
        if safety.get("human_approval_required") is not True:
            block("HUMAN_APPROVAL_MISSING", "所有候选必须要求人工批准")

    recommendations = result.get("recommendations")
    if not isinstance(recommendations, list):
        block("RECOMMENDATIONS_INVALID", "recommendations必须为数组")
        recommendations = []
    else:
        for index, item in enumerate(recommendations):
            if not isinstance(item, dict) or item.get("approval_required") is not True:
                block("RECOMMENDATION_APPROVAL_MISSING", f"第{index + 1}条建议缺少人工批准门")

    if preprocessing.get("status") == "DATA_BLOCKED":
        block("PREPROCESSING_DATA_BLOCKED", "确定性预处理未通过，Validator不得放行")
        if result.get("status") == "READY_FOR_HUMAN_REVIEW":
            block("BLOCKED_DATA_PROMOTED", "预处理已阻断，结果不得进入人工方案确认")

    context = preprocessing.get("agents_context")
    if preprocessing.get("status") == "READY_FOR_ANALYSIS":
        for code in verify_agents_analysis_context(ROOT, request, preprocessing):
            block(code, "AGENTS执行上下文与服务端项目真源不一致")
        for code in verify_tool_receipts(ROOT, request, preprocessing):
            block(code, "确定性工具回执缺失或与当前输入、配置、输出不一致")

    aggregation_only = request.get("intent") == "AGGREGATE_REPORTS" or (
        request.get("intent") == "OLD_PRODUCT_OPTIMIZATION"
        and request.get("fields", {}).get("workflow_phase") in {"AGGREGATE_ONLY", "AGGREGATED"}
    )
    provenance = result.get("provenance")
    if not isinstance(provenance, dict):
        block("PROVENANCE_MISSING", "结果缺少AGENTS/Codex来源证明")
        provenance = {}
    if aggregation_only:
        if provenance.get("decision_engine") != "DETERMINISTIC_TOOL_ONLY" or provenance.get("codex_invoked") is not False:
            block("AGGREGATION_PROVENANCE_INVALID", "纯数据聚合阶段不得伪装成Codex业务结论")
        if recommendations:
            block("AGGREGATION_RECOMMENDATION_FORBIDDEN", "纯数据聚合阶段不得生成广告建议")
    elif preprocessing.get("status") == "READY_FOR_ANALYSIS" and result.get("status") == "READY_FOR_HUMAN_REVIEW":
        if provenance.get("decision_engine") != "CODEX_AGENTS" or provenance.get("codex_invoked") is not True:
            block("CODEX_PROVENANCE_REQUIRED", "业务结论必须来自本次Codex+AGENTS调用")
        actual_digest = context.get("context_digest") if isinstance(context, dict) else None
        if provenance.get("agents_context_digest") != actual_digest:
            block("RESULT_CONTEXT_DIGEST_MISMATCH", "结果未绑定本次AGENTS执行上下文")
        required_sources = set(context.get("required_codex_sources") or []) if isinstance(context, dict) else set()
        sources_read = set(provenance.get("sources_read") or [])
        if sources_read != required_sources:
            block("CODEX_SOURCE_COVERAGE_MISMATCH", "Codex未声明完整读取本次八层、规则、阈值、工具和合同")
        required_receipts = set(context.get("tool_receipt_ids") or []) if isinstance(context, dict) else set()
        if set(provenance.get("tool_receipt_ids") or []) != required_receipts:
            block("CODEX_TOOL_RECEIPT_MISMATCH", "Codex结果未绑定本次工具回执")
        for code in _verify_codex_receipt(result, preprocessing):
            block(code, "Codex调用凭证或原始输出不一致")

        allowed_sources = _registered_sources(context) if isinstance(context, dict) else set()
        for index, item in enumerate(recommendations):
            evidence_sources = set(item.get("evidence_sources") or []) if isinstance(item, dict) else set()
            if not evidence_sources or not evidence_sources <= allowed_sources:
                block("RECOMMENDATION_EVIDENCE_UNREGISTERED", f"第{index + 1}条建议引用了未登记证据")
        for index, row in enumerate(result.get("new_product_architecture") or []):
            evidence_sources = set(row.get("evidence_sources") or []) if isinstance(row, dict) else set()
            if not evidence_sources or not evidence_sources <= allowed_sources:
                block("ARCHITECTURE_EVIDENCE_UNREGISTERED", f"第{index + 1}条新品架构引用了未登记证据")

    if request.get("intent") == "NEW_PRODUCT_PROMOTION" and preprocessing.get("status") == "READY_FOR_ANALYSIS":
        if preprocessing.get("match_type_data_status") != "READY":
            block("MATCH_TYPE_DATA_PENDING", "新品相关性表或搜索词月搜索量表尚未补充")
        product_count = preprocessing.get("product_count")
        analysis_asins = preprocessing.get("analysis_asins")
        if not isinstance(product_count, int) or product_count < 1:
            block("NEW_PRODUCT_COUNT_INVALID", "广告架构设计缺少有效产品数量")
        if not isinstance(analysis_asins, list) or len(analysis_asins) != product_count:
            block("NEW_PRODUCT_ASIN_COUNT_MISMATCH", "产品数量与已分析ASIN数量不一致")
        elif len(set(str(item) for item in analysis_asins)) != len(analysis_asins):
            block("NEW_PRODUCT_ASIN_DUPLICATE", "广告架构设计包含重复ASIN")
        allowed_asins = {str(item) for item in analysis_asins or []}
        rows = result.get("new_product_architecture")
        if not isinstance(rows, list):
            block("NEW_PRODUCT_ARCHITECTURE_INVALID", "Codex结果缺少结构化新品广告架构")
        else:
            for index, row in enumerate(rows):
                if not isinstance(row, dict) or row.get("asin") not in allowed_asins:
                    block("NEW_PRODUCT_ARCHITECTURE_ASIN_INVALID", f"第{index + 1}条架构ASIN不在本次任务范围")
                if isinstance(row, dict) and row.get("approval_required") is not True:
                    block("NEW_PRODUCT_ARCHITECTURE_APPROVAL_MISSING", f"第{index + 1}条架构缺少人工批准门")
        input_mode = str(preprocessing.get("input_mode") or "manual")
        if input_mode == "manual" and isinstance(product_count, int) and product_count > 10:
            block("MANUAL_PRODUCT_LIMIT_EXCEEDED", "手动录入超过10个ASIN上限")
        raw_products = request.get("fields", {}).get("products_json")
        if raw_products:
            try:
                submitted_products = json.loads(str(raw_products))
                if not isinstance(submitted_products, list) or len(submitted_products) != product_count:
                    block("NEW_PRODUCT_REQUEST_COUNT_MISMATCH", "提交产品清单与预处理数量不一致")
            except json.JSONDecodeError:
                block("NEW_PRODUCT_REQUEST_INVALID", "提交产品清单JSON无效")

    if require_final_artifacts and result.get("status") == "READY_FOR_HUMAN_REVIEW":
        for code in _verify_final_artifacts(result, preprocessing):
            block(code, "最终网页下载文件缺失或与已验证结果不一致")

    serialized = str(result)
    for forbidden in ("EXECUTED_SUCCESS", "AMAZON_ACTION_APPLIED", "PRODUCTION_ACTIVE"):
        if forbidden in serialized:
            block("EXECUTION_CLAIM_FORBIDDEN", f"结果包含禁止执行声明: {forbidden}")
    return {
        "schema_version": "2.1",
        "job_id": request.get("job_id"),
        "outcome": "BLOCKED" if findings else "PASS_CANDIDATE_ONLY",
        "findings": findings,
        "execution_allowed": False,
        "human_approval_required": True,
    }
