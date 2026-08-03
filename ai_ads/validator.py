from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal

from .contracts import (
    ActionType,
    AdContext,
    AdDecisionPacket,
    AdPlanCandidate,
    AdProductType,
    ArbitrationResult,
    CandidateAction,
    DataMode,
    DataQualityStatus,
    FindingLevel,
    ObjectType,
    RiskLevel,
    RulePackageReference,
    RuleSourceStatus,
    RunMode,
    StrategyProfile,
    ValidationFinding,
    ValidationOutcome,
    ValidationReport,
)
from .data_quality import assess_data_quality


EXECUTABLE_ACTIONS = {
    ActionType.INCREASE_BUDGET,
    ActionType.DECREASE_BUDGET,
    ActionType.INCREASE_BID,
    ActionType.DECREASE_BID,
    ActionType.SET_PLACEMENT,
    ActionType.PAUSE,
    ActionType.ENABLE,
    ActionType.NEGATIVE_EXACT,
    ActionType.CREATE_STRUCTURE,
}

DESTRUCTIVE_ACTIONS = {
    ActionType.PAUSE,
    ActionType.NEGATIVE_EXACT,
    ActionType.DECREASE_BUDGET,
    ActionType.DECREASE_BID,
}

PRODUCTION_EXECUTION_ENABLED = False

NUMERIC_ACTIONS = {
    ActionType.INCREASE_BUDGET,
    ActionType.DECREASE_BUDGET,
    ActionType.INCREASE_BID,
    ActionType.DECREASE_BID,
    ActionType.SET_PLACEMENT,
}

ACTION_OBJECT_TYPES = {
    ActionType.INCREASE_BUDGET: {ObjectType.CAMPAIGN},
    ActionType.DECREASE_BUDGET: {ObjectType.CAMPAIGN},
    ActionType.INCREASE_BID: {ObjectType.AD_GROUP, ObjectType.TARGET},
    ActionType.DECREASE_BID: {ObjectType.AD_GROUP, ObjectType.TARGET},
    ActionType.SET_PLACEMENT: {ObjectType.PLACEMENT},
}


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _object_exists(action: CandidateAction, packet: AdDecisionPacket) -> bool:
    known = {
        ObjectType.CAMPAIGN: {item.campaign_id for item in packet.campaigns},
        ObjectType.AD_GROUP: {item.ad_group_id for item in packet.ad_groups},
        ObjectType.TARGET: {item.target_id for item in packet.targets},
        ObjectType.SEARCH_TERM: {
            item.search_term_key for item in packet.search_terms
        },
        ObjectType.ADVERTISED_PRODUCT: {
            metric.object_id
            for metric in packet.metrics
            if metric.object_type == ObjectType.ADVERTISED_PRODUCT
        },
        ObjectType.PLACEMENT: {
            metric.object_id
            for metric in packet.metrics
            if metric.object_type == ObjectType.PLACEMENT
        },
    }
    if action.object_type == ObjectType.STRUCTURE:
        return action.action_type == ActionType.CREATE_STRUCTURE
    return action.object_id in known.get(action.object_type, set())


def _validate_action(
    action: CandidateAction,
    packet: AdDecisionPacket,
    context: AdContext,
    now: datetime,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    if not _object_exists(action, packet):
        findings.append(
            ValidationFinding(
                code="ACTION_OBJECT_NOT_FOUND",
                level=FindingLevel.BLOCK,
                message="动作无法定位到输入快照中的唯一对象",
                action_id=action.candidate_action_id,
                object_id=action.object_id,
            )
        )

    allowed_object_types = ACTION_OBJECT_TYPES.get(action.action_type)
    if allowed_object_types is not None and action.object_type not in allowed_object_types:
        findings.append(
            ValidationFinding(
                code="ACTION_OBJECT_TYPE_MISMATCH",
                level=FindingLevel.BLOCK,
                message=(
                    f"{action.action_type.value}不支持对象类型"
                    f"{action.object_type.value}"
                ),
                action_id=action.candidate_action_id,
                object_id=action.object_id,
            )
        )

    if action.action_type in EXECUTABLE_ACTIONS:
        required_values = {
            "current_value": action.current_value,
            "proposed_value": action.proposed_value,
            "expected_current_value": action.expected_current_value,
            "rollback_value": action.rollback_value,
            "unit": action.unit,
            "threshold_id": action.threshold_id,
        }
        missing = [name for name, value in required_values.items() if value is None]
        if missing:
            findings.append(
                ValidationFinding(
                    code="EXECUTION_FIELDS_MISSING",
                    level=FindingLevel.BLOCK,
                    message="执行字段缺失: " + ", ".join(missing),
                    action_id=action.candidate_action_id,
                    object_id=action.object_id,
                )
            )
        if action.expected_current_value != action.current_value:
            findings.append(
                ValidationFinding(
                    code="EXPECTED_CURRENT_VALUE_MISMATCH",
                    level=FindingLevel.BLOCK,
                    message="expected_current_value与方案当前值不一致",
                    action_id=action.candidate_action_id,
                    object_id=action.object_id,
                )
            )
        if not action.reversible:
            findings.append(
                ValidationFinding(
                    code="ACTION_NOT_REVERSIBLE",
                    level=FindingLevel.APPROVAL,
                    message="动作不可逆或无法完整回滚",
                    action_id=action.candidate_action_id,
                    object_id=action.object_id,
                )
            )

    if action.action_type in NUMERIC_ACTIONS:
        numeric_values = {
            "current_value": action.current_value,
            "proposed_value": action.proposed_value,
            "expected_current_value": action.expected_current_value,
            "rollback_value": action.rollback_value,
        }
        invalid_types = [
            name for name, value in numeric_values.items() if not isinstance(value, Decimal)
        ]
        if invalid_types:
            findings.append(
                ValidationFinding(
                    code="NUMERIC_ACTION_VALUE_INVALID",
                    level=FindingLevel.BLOCK,
                    message="数值动作字段必须为Decimal: " + ", ".join(invalid_types),
                    action_id=action.candidate_action_id,
                    object_id=action.object_id,
                )
            )
        else:
            non_finite_values = [
                name for name, value in numeric_values.items() if not value.is_finite()
            ]
            if non_finite_values:
                findings.append(
                    ValidationFinding(
                        code="NUMERIC_ACTION_VALUE_NON_FINITE",
                        level=FindingLevel.BLOCK,
                        message="数值动作字段必须是有限数: " + ", ".join(non_finite_values),
                        action_id=action.candidate_action_id,
                        object_id=action.object_id,
                    )
                )
            else:
                negative_values = [
                    name for name, value in numeric_values.items() if value < Decimal("0")
                ]
                if negative_values:
                    findings.append(
                        ValidationFinding(
                            code="NUMERIC_ACTION_VALUE_NEGATIVE",
                            level=FindingLevel.BLOCK,
                            message="数值动作字段不得为负数: " + ", ".join(negative_values),
                            action_id=action.candidate_action_id,
                            object_id=action.object_id,
                        )
                    )
                current = action.current_value
                proposed = action.proposed_value
                if (
                    action.action_type in {ActionType.INCREASE_BUDGET, ActionType.INCREASE_BID}
                    and proposed <= current
                ):
                    findings.append(
                        ValidationFinding(
                            code="ACTION_DIRECTION_INVALID",
                            level=FindingLevel.BLOCK,
                            message="增加动作的proposed_value必须大于current_value",
                            action_id=action.candidate_action_id,
                            object_id=action.object_id,
                        )
                    )
                if (
                    action.action_type in {ActionType.DECREASE_BUDGET, ActionType.DECREASE_BID}
                    and proposed >= current
                ):
                    findings.append(
                        ValidationFinding(
                            code="ACTION_DIRECTION_INVALID",
                            level=FindingLevel.BLOCK,
                            message="降低动作的proposed_value必须小于current_value",
                            action_id=action.candidate_action_id,
                            object_id=action.object_id,
                        )
                    )

    if not _is_timezone_aware(action.valid_until):
        findings.append(
            ValidationFinding(
                code="ACTION_TIMEZONE_MISSING",
                level=FindingLevel.BLOCK,
                message="动作有效期必须包含时区",
                action_id=action.candidate_action_id,
                object_id=action.object_id,
            )
        )
    elif action.valid_until <= now:
        findings.append(
            ValidationFinding(
                code="ACTION_EXPIRED",
                level=FindingLevel.BLOCK,
                message="动作已过有效期",
                action_id=action.candidate_action_id,
                object_id=action.object_id,
            )
        )

    if (
        action.object_id in context.protected_entities
        and action.action_type in DESTRUCTIVE_ACTIONS
    ):
        findings.append(
            ValidationFinding(
                code="PROTECTED_ENTITY_ACTION",
                level=FindingLevel.BLOCK,
                message="受保护对象不得执行收缩或否定动作",
                action_id=action.candidate_action_id,
                object_id=action.object_id,
            )
        )

    if action.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        findings.append(
            ValidationFinding(
                code="HIGH_IMPACT_ACTION",
                level=FindingLevel.APPROVAL,
                message="高影响动作需要人工审批",
                action_id=action.candidate_action_id,
                object_id=action.object_id,
            )
        )
    elif action.action_type in {ActionType.PAUSE, ActionType.NEGATIVE_EXACT}:
        findings.append(
            ValidationFinding(
                code="HIGH_IMPACT_RISK_MISCLASSIFIED",
                level=FindingLevel.BLOCK,
                message="暂停或精准否定不得标记为低/中风险",
                action_id=action.candidate_action_id,
                object_id=action.object_id,
            )
        )
    return findings


def _budget_increase(actions: list[CandidateAction]) -> Decimal:
    total = Decimal("0")
    for action in actions:
        if (
            action.action_type == ActionType.INCREASE_BUDGET
            and isinstance(action.current_value, Decimal)
            and isinstance(action.proposed_value, Decimal)
        ):
            total += max(action.proposed_value - action.current_value, Decimal("0"))
    return total


def validate_plan(
    *,
    packet: AdDecisionPacket,
    context: AdContext,
    package: RulePackageReference,
    arbitration: ArbitrationResult,
    plan: AdPlanCandidate,
    run_mode: RunMode,
    now: datetime | None = None,
) -> ValidationReport:
    now = now or datetime.now(timezone.utc)
    findings: list[ValidationFinding] = []
    if not _is_timezone_aware(now):
        findings.append(
            ValidationFinding(
                code="VALIDATION_CLOCK_TIMEZONE_MISSING",
                level=FindingLevel.BLOCK,
                message="Validator当前时间必须包含时区",
            )
        )
        now = now.replace(tzinfo=timezone.utc)
    data_quality = assess_data_quality(packet)
    findings.extend(data_quality.findings)

    if not _is_timezone_aware(context.valid_until):
        findings.append(
            ValidationFinding(
                code="AD_CONTEXT_TIMEZONE_MISSING",
                level=FindingLevel.BLOCK,
                message="AdContext有效期必须包含时区",
            )
        )
    elif context.valid_until <= now:
        findings.append(
            ValidationFinding(
                code="AD_CONTEXT_EXPIRED",
                level=FindingLevel.BLOCK,
                message="AdContext已过有效期",
            )
        )
    if not _is_timezone_aware(plan.metadata.valid_until):
        findings.append(
            ValidationFinding(
                code="PLAN_TIMEZONE_MISSING",
                level=FindingLevel.BLOCK,
                message="方案有效期必须包含时区",
            )
        )
    elif plan.metadata.valid_until <= now:
        findings.append(
            ValidationFinding(
                code="PLAN_EXPIRED",
                level=FindingLevel.BLOCK,
                message="方案已过有效期",
            )
        )

    if context.category.strip().lower() not in {"rug", "rugs"}:
        findings.append(
            ValidationFinding(
                code="UNSUPPORTED_CATEGORY",
                level=FindingLevel.BLOCK,
                message="陆遥广告智能体只支持 Rug / 地毯",
            )
        )

    if package.rule_file_sha256 is None or package.threshold_file_sha256 is None:
        findings.append(
            ValidationFinding(
                code="RULE_PACKAGE_FILE_CHECKSUM_MISSING",
                level=FindingLevel.BLOCK,
                message="规则包必须分别保存规则文件和阈值文件 SHA-256",
            )
        )

    if context.ad_product_type != AdProductType.SP:
        findings.append(
            ValidationFinding(
                code="UNSUPPORTED_AD_PRODUCT",
                level=FindingLevel.BLOCK,
                message="第一阶段只支持SP",
            )
        )
    elif context.strategy_profile == StrategyProfile.SP_COLD_START:
        findings.append(
            ValidationFinding(
                code="CAPABILITY_NOT_ACTIVE",
                level=FindingLevel.BLOCK,
                message="SP冷启动当前未激活",
            )
        )
    elif context.strategy_profile != StrategyProfile.SP_STANDARD_OPTIMIZATION:
        findings.append(
            ValidationFinding(
                code="UNSUPPORTED_STRATEGY_PROFILE",
                level=FindingLevel.BLOCK,
                message="StrategyProfile不受支持",
            )
        )

    if run_mode == RunMode.PRODUCTION:
        if not PRODUCTION_EXECUTION_ENABLED:
            findings.append(
                ValidationFinding(
                    code="PRODUCTION_EXECUTION_DISABLED",
                    level=FindingLevel.BLOCK,
                    message="V2.0当前固定为HUMAN_EXECUTION_ONLY，生产执行未启用",
                )
            )
        if package.rule_source_status != RuleSourceStatus.ACTIVE:
            findings.append(
                ValidationFinding(
                    code="RULE_SOURCE_NOT_ACTIVE",
                    level=FindingLevel.BLOCK,
                    message="唯一规则源尚未确定或未激活",
                )
            )
        if package.threshold_source_status != RuleSourceStatus.ACTIVE:
            findings.append(
                ValidationFinding(
                    code="THRESHOLD_SOURCE_NOT_ACTIVE",
                    level=FindingLevel.BLOCK,
                    message="阈值源尚未确定或未激活",
                )
            )
    else:
        if package.rule_source_status == RuleSourceStatus.UNDECIDED:
            findings.append(
                ValidationFinding(
                    code="RULE_SOURCE_UNDECIDED_TEST_ONLY",
                    level=FindingLevel.APPROVAL,
                    message="规则源未决定，结果只能用于结构测试",
                )
            )
        if package.threshold_source_status == RuleSourceStatus.UNDECIDED:
            findings.append(
                ValidationFinding(
                    code="THRESHOLD_SOURCE_UNDECIDED_TEST_ONLY",
                    level=FindingLevel.APPROVAL,
                    message="阈值源未决定，结果只能用于结构测试",
                )
            )

    metadata_checks = (
        (
            plan.metadata.batch_id == arbitration.batch_id,
            "PLAN_BATCH_MISMATCH",
            "方案、仲裁结果Batch ID不一致",
        ),
        (
            plan.metadata.data_snapshot_id == packet.metadata.data_snapshot_id,
            "PLAN_SNAPSHOT_MISMATCH",
            "方案与数据快照不一致",
        ),
        (
            plan.metadata.ad_context_version == context.ad_context_version,
            "PLAN_CONTEXT_MISMATCH",
            "方案与AdContext版本不一致",
        ),
        (
            plan.metadata.rule_package_version == package.rule_package_version,
            "PLAN_RULE_VERSION_MISMATCH",
            "方案与规则包版本不一致",
        ),
        (
            plan.metadata.rule_package_checksum == package.rule_package_checksum,
            "PLAN_RULE_CHECKSUM_MISMATCH",
            "方案与规则包校验值不一致",
        ),
    )
    for passed, code, message in metadata_checks:
        if not passed:
            findings.append(
                ValidationFinding(code=code, level=FindingLevel.BLOCK, message=message)
            )

    if arbitration.conflicts:
        for conflict in arbitration.conflicts:
            findings.append(
                ValidationFinding(
                    code=conflict.code,
                    level=FindingLevel.BLOCK,
                    message=conflict.message,
                    object_id=conflict.object_id,
                )
            )

    selected_id_counts = Counter(
        item.candidate_action_id for item in arbitration.selected_actions
    )
    plan_id_counts = Counter(item.candidate_action_id for item in plan.actions)
    for source_name, counts in (
        ("仲裁结果", selected_id_counts),
        ("方案", plan_id_counts),
    ):
        for action_id, count in sorted(counts.items()):
            if count > 1:
                findings.append(
                    ValidationFinding(
                        code="DUPLICATE_ACTION_ID",
                        level=FindingLevel.BLOCK,
                        message=f"{source_name}中动作ID重复: {action_id}，数量={count}",
                        action_id=action_id,
                    )
                )
    if selected_id_counts != plan_id_counts:
        findings.append(
            ValidationFinding(
                code="PLAN_ACTION_SET_MISMATCH",
                level=FindingLevel.BLOCK,
                message="方案动作集合与仲裁选中动作不一致",
            )
        )

    primary_keys: set[tuple[ObjectType, str]] = set()
    for action in plan.actions:
        if action.is_primary:
            key = (action.object_type, action.object_id)
            if key in primary_keys:
                findings.append(
                    ValidationFinding(
                        code="MULTIPLE_PRIMARY_ACTIONS",
                        level=FindingLevel.BLOCK,
                        message="同一对象存在多个主动作",
                        action_id=action.candidate_action_id,
                        object_id=action.object_id,
                    )
                )
            primary_keys.add(key)
        findings.extend(_validate_action(action, packet, context, now))

    if packet.metadata.data_mode == DataMode.LIMITED and any(
        item.action_type in EXECUTABLE_ACTIONS for item in plan.actions
    ):
        findings.append(
            ValidationFinding(
                code="LIMITED_DATA_EXECUTION_FORBIDDEN",
                level=FindingLevel.BLOCK,
                message="有限数据模式不得输出执行动作",
            )
        )

    budget_increase = _budget_increase(plan.actions)
    if budget_increase > 0:
        if context.batch_budget_change_cap is None:
            findings.append(
                ValidationFinding(
                    code="BATCH_BUDGET_CAP_NOT_CONFIGURED",
                    level=FindingLevel.APPROVAL,
                    message="存在预算增加动作，但批次预算变化上限未配置",
                )
            )
        elif budget_increase > context.batch_budget_change_cap:
            findings.append(
                ValidationFinding(
                    code="BATCH_BUDGET_CAP_EXCEEDED",
                    level=FindingLevel.BLOCK,
                    message=(
                        f"批次预算增加{budget_increase}超过上限"
                        f"{context.batch_budget_change_cap}"
                    ),
                )
            )

    if data_quality.status == DataQualityStatus.DQ_WARNING:
        findings.append(
            ValidationFinding(
                code="DATA_QUALITY_REQUIRES_APPROVAL",
                level=FindingLevel.APPROVAL,
                message="数据质量存在警告，不能自动通过",
            )
        )

    if any(item.level == FindingLevel.BLOCK for item in findings):
        outcome = ValidationOutcome.BLOCKED
    elif any(item.level == FindingLevel.APPROVAL for item in findings):
        outcome = ValidationOutcome.APPROVAL_REQUIRED
    else:
        outcome = ValidationOutcome.AUTO_PASS

    return ValidationReport(
        plan_id=plan.metadata.plan_id,
        batch_id=plan.metadata.batch_id,
        outcome=outcome,
        findings=findings,
    )
