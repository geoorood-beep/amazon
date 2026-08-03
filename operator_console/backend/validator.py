from __future__ import annotations

from typing import Any


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


def validate_operator_result(
    result: dict[str, Any], request: dict[str, Any], preprocessing: dict[str, Any]
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
    else:
        for index, item in enumerate(recommendations):
            if not isinstance(item, dict) or item.get("approval_required") is not True:
                block("RECOMMENDATION_APPROVAL_MISSING", f"第{index + 1}条建议缺少人工批准门")
    if preprocessing.get("status") == "DATA_BLOCKED" and result.get("status") == "READY_FOR_HUMAN_REVIEW":
        block("BLOCKED_DATA_PROMOTED", "预处理已阻断，结果不得进入人工方案确认")
    serialized = str(result)
    for forbidden in ("EXECUTED_SUCCESS", "AMAZON_ACTION_APPLIED", "PRODUCTION_ACTIVE"):
        if forbidden in serialized:
            block("EXECUTION_CLAIM_FORBIDDEN", f"结果包含禁止执行声明: {forbidden}")
    return {
        "schema_version": "1.0",
        "job_id": request.get("job_id"),
        "outcome": "BLOCKED" if findings else "PASS_CANDIDATE_ONLY",
        "findings": findings,
        "execution_allowed": False,
        "human_approval_required": True,
    }
