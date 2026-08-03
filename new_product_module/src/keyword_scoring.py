from __future__ import annotations

import re
from typing import Any

from .schemas import BlockedItem, CategoryRules, KeywordScore, ProductInfo, StageMatchedKeyword


_SIZE_PATTERN = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|['’′])?\s*"
    r"(?:x|×|by)\s*(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|['’′])?(?![\d.])",
    re.IGNORECASE,
)

_DEFAULT_ATTRIBUTE_ALIASES: dict[str, dict[str, list[str]]] = {
    "rug_type": {
        "area_rug": ["area rug", "area rugs"],
        "runner": ["runner rug", "runner rugs", "rug runner", "rug runners", "hallway runner"],
        "doormat": ["doormat", "doormats", "door mat", "door mats", "welcome mat", "entry mat"],
        "round": ["round rug", "round rugs", "circular rug", "circle rug"],
        "bathroom_rug": ["bathroom rug", "bathroom rugs", "bath rug", "bath rugs", "bath mat", "bath mats"],
        "kitchen_rug": ["kitchen rug", "kitchen rugs", "kitchen mat", "kitchen mats"],
        "outdoor_rug": ["outdoor rug", "outdoor rugs", "patio rug", "patio rugs"],
    },
    "style": {
        "vintage": ["vintage"],
        "modern": ["modern"],
        "boho": ["boho", "bohemian"],
        "traditional": ["traditional"],
        "farmhouse": ["farmhouse"],
        "abstract": ["abstract"],
        "geometric": ["geometric"],
        "oriental": ["oriental"],
        "contemporary": ["contemporary"],
        "retro": ["retro"],
    },
    "color": {
        "blue": ["blue"],
        "navy": ["navy", "navy blue"],
        "red": ["red"],
        "green": ["green"],
        "black": ["black"],
        "white": ["white"],
        "gray": ["gray", "grey"],
        "pink": ["pink"],
        "brown": ["brown"],
        "beige": ["beige"],
        "cream": ["cream", "ivory"],
        "orange": ["orange"],
        "yellow": ["yellow"],
        "purple": ["purple"],
    },
    "material": {
        "wool": ["wool", "woolen"],
        "faux_wool": ["faux wool"],
        "cotton": ["cotton"],
        "jute": ["jute"],
        "polyester": ["polyester"],
        "polypropylene": ["polypropylene"],
        "nylon": ["nylon"],
        "chenille": ["chenille"],
        "silk": ["silk"],
        "bamboo": ["bamboo"],
    },
    "shape": {
        "round": ["round", "circular", "circle"],
        "oval": ["oval"],
        "square": ["square"],
        "rectangular": ["rectangular", "rectangle"],
    },
    "animal_pattern": {
        "leopard": ["leopard"],
        "tiger": ["tiger"],
        "zebra": ["zebra"],
        "cowhide": ["cowhide", "cow hide"],
        "bear": ["bear"],
        "deer": ["deer"],
        "dog": ["dog"],
        "cat": ["cat"],
        "horse": ["horse"],
        "elephant": ["elephant"],
    },
}


def score_keywords(
    rows: list[StageMatchedKeyword],
    product: ProductInfo,
    rules: CategoryRules,
) -> tuple[list[KeywordScore], list[BlockedItem]]:
    blocked: list[BlockedItem] = []
    scores: list[KeywordScore] = []
    baseline = rules.rug_type_baselines.get(product.rug_type)

    if baseline is None:
        return [], [
            BlockedItem(
                item_type="product",
                identifier=product.rug_type,
                source_step="keyword_scoring",
                reason="规则缺失：产品地毯类型未在 rug_type_baselines 中配置",
            )
        ]

    for row in rows:
        score, missing = _score_one_keyword(row, product, rules, baseline.cvr_baseline)
        scores.append(score)
        issues = list(score.attribute_conflicts) + missing
        if issues:
            blocked.append(
                BlockedItem(
                    item_type="keyword",
                    identifier=row.search_term,
                    source_step="keyword_scoring",
                    reason="; ".join(dict.fromkeys(issues)),
                    data=score.model_dump(),
                )
            )
    return scores, blocked


def _score_one_keyword(
    row: StageMatchedKeyword,
    product: ProductInfo,
    rules: CategoryRules,
    target_cvr: float | None,
) -> tuple[KeywordScore, list[str]]:
    missing: list[str] = []
    override = _keyword_override(row.search_term, rules)
    attribute_conflicts, attribute_unconfirmed = _detect_product_attribute_issues(
        row.search_term, product, rules
    )
    missing.extend(attribute_unconfirmed)

    transaction_score = override.get("transaction_data_score")
    if transaction_score is None:
        if target_cvr is None:
            missing.append("规则缺失：cvr_baseline")
        elif target_cvr <= 0:
            missing.append("规则错误：cvr_baseline 必须大于 0")
        else:
            multiplier = rules.scoring_weights.cvr_score_multiplier
            transaction_score = min(row.cvr / target_cvr / multiplier, 1) * 100

    region_score, region_missing, region_hard_conflict = _attribute_score(
        "region", row.search_term, product.region_tags, rules, override
    )
    spec_score, spec_missing, spec_hard_conflict = _attribute_score(
        "spec", row.search_term, [product.size_spec, product.material], rules, override
    )
    style_score, style_missing, style_hard_conflict = _attribute_score(
        "style", row.search_term, [product.style], rules, override
    )
    color_score, color_missing, color_hard_conflict = _attribute_score(
        "color", row.search_term, [product.color], rules, override
    )
    missing.extend(region_missing + spec_missing + style_missing + color_missing)
    static_hard_conflict = any(
        [region_hard_conflict, spec_hard_conflict, style_hard_conflict, color_hard_conflict]
    )
    if static_hard_conflict and not attribute_conflicts:
        attribute_conflicts.append("产品属性命中规则库硬冲突词")
    hard_conflict = bool(attribute_conflicts) or static_hard_conflict

    components = [transaction_score, region_score, spec_score, style_score, color_score]
    total_score = override.get("total_match_score")
    if total_score is None and all(component is not None for component in components):
        weights = rules.scoring_weights
        total_score = (
            float(transaction_score) * weights.transaction_data
            + float(region_score) * weights.region_match
            + float(spec_score) * weights.spec_match
            + float(style_score) * weights.style_match
            + float(color_score) * weights.color_match
        )

    if row.stage_min_match_score is None:
        missing.append("规则缺失：stage.min_match_score")

    conclusion = "待人工确认"
    reasons = list(row.pool_reasons)
    needs_review = bool(row.needs_review)
    if hard_conflict:
        conclusion = "不建议投放"
        reasons.extend(attribute_conflicts)
    elif missing:
        needs_review = True
        reasons.extend(missing)
    elif not row.aba_stage_ok:
        conclusion = "ABA超出阶段范围，受限测试"
        needs_review = True
        reasons.append(row.aba_stage_status)
    elif float(total_score) >= float(row.stage_min_match_score):
        conclusion = "建议投放"
    else:
        conclusion = "受限测试"
        needs_review = True
        reasons.append("总匹配度未达到当前阶段最低匹配度")

    score = KeywordScore(
        asin=product.asin or product.sku,
        order_stage=row.order_stage,
        search_term=row.search_term,
        clicks=row.clicks,
        orders=row.orders,
        cvr=row.cvr,
        aba_rank=row.aba_rank,
        transaction_data_score=_round_score(transaction_score),
        region_score=_round_score(region_score),
        spec_score=_round_score(spec_score),
        style_score=_round_score(style_score),
        color_score=_round_score(color_score),
        total_match_score=_round_score(total_score),
        conclusion=conclusion,
        reasons=reasons,
        needs_review=needs_review,
        hard_conflict=hard_conflict,
        attribute_conflicts=attribute_conflicts,
        aba_stage_ok=row.aba_stage_ok,
    )
    return score, missing


def _keyword_override(search_term: str, rules: CategoryRules) -> dict[str, Any]:
    overrides = rules.attribute_scoring.get("keyword_score_overrides", {})
    return overrides.get(_normalize_term(search_term), overrides.get(search_term, {})) or {}


def _attribute_score(
    name: str,
    search_term: str,
    product_values: list[str | None] | list[str],
    rules: CategoryRules,
    override: dict[str, Any],
) -> tuple[float | None, list[str], bool]:
    override_key = f"{name}_score"
    if override_key in override:
        return float(override[override_key]), [], False

    config = rules.attribute_scoring.get(name, {})
    term = _normalize_term(search_term)
    hard_conflict_terms = [_normalize_term(item) for item in config.get("hard_conflict_terms", [])]
    if any(term_part in term for term_part in hard_conflict_terms):
        return 0, [], True

    candidates = [_normalize_term(value) for value in product_values if value]
    if any(candidate and candidate in term for candidate in candidates):
        return 100, [], False

    neutral_score = config.get("neutral_score")
    if neutral_score is not None and not _contains_any_known_attribute(term, config):
        return float(neutral_score), [], False

    partial_score = config.get("partial_match_score")
    if partial_score is not None:
        return float(partial_score), [], False

    return None, [f"规则缺失：attribute_scoring.{name}.partial_match_score"], False


def _contains_any_known_attribute(term: str, config: dict[str, Any]) -> bool:
    known_terms = [_normalize_term(item) for item in config.get("known_terms", [])]
    return any(item and item in term for item in known_terms)


def _detect_product_attribute_issues(
    search_term: str,
    product: ProductInfo,
    rules: CategoryRules,
) -> tuple[list[str], list[str]]:
    term = _normalize_term(search_term)
    conflicts: list[str] = []
    unconfirmed: list[str] = []

    keyword_sizes = _extract_sizes(search_term)
    if keyword_sizes:
        target_sizes = _extract_sizes(product.size_spec)
        if not target_sizes:
            unconfirmed.append("产品信息缺失：目标推广尺寸，无法确认关键词明确尺寸")
        elif not keyword_sizes.issubset(target_sizes):
            conflicts.append(
                "尺寸硬冲突：目标尺寸 "
                f"{_display_sizes(target_sizes)}，关键词尺寸 {_display_sizes(keyword_sizes)}"
            )

    checks = [
        ("rug_type", "地毯类型", product.rug_type),
        ("style", "风格", product.style),
        ("color", "颜色", product.color),
        ("material", "材质", product.material),
        ("shape", "形状", product.shape),
        ("animal_pattern", "图案动物类型", product.animal_pattern),
    ]
    for key, label, product_value in checks:
        aliases = _attribute_aliases(key, rules)
        term_values = _matched_canonical_values(term, aliases)
        if not term_values:
            continue
        product_values = _matched_canonical_values(_normalize_term(product_value), aliases)
        if not product_value:
            unconfirmed.append(f"产品信息缺失：{label}，无法确认关键词明确属性 {', '.join(sorted(term_values))}")
        elif not product_values:
            unconfirmed.append(f"规则未识别产品{label}：{product_value}，无法核对关键词明确属性")
        elif term_values.isdisjoint(product_values):
            conflicts.append(
                f"{label}硬冲突：产品={product_value}，关键词={', '.join(sorted(term_values))}"
            )

    return list(dict.fromkeys(conflicts)), list(dict.fromkeys(unconfirmed))


def _extract_sizes(value: str | None) -> set[tuple[str, str]]:
    if not value:
        return set()
    sizes: set[tuple[str, str]] = set()
    for width, length in _SIZE_PATTERN.findall(str(value)):
        dimensions = sorted((_normalize_dimension(width), _normalize_dimension(length)), key=float)
        sizes.add((dimensions[0], dimensions[1]))
    return sizes


def _normalize_dimension(value: str) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.4f}".rstrip("0").rstrip(".")


def _display_sizes(sizes: set[tuple[str, str]]) -> str:
    return "/".join(f"{width}x{length}" for width, length in sorted(sizes, key=lambda item: tuple(map(float, item))))


def _attribute_aliases(name: str, rules: CategoryRules) -> dict[str, list[str]]:
    aliases = {
        canonical: list(values)
        for canonical, values in _DEFAULT_ATTRIBUTE_ALIASES.get(name, {}).items()
    }
    configured = rules.attribute_scoring.get(name, {}).get("value_aliases", {}) or {}
    for canonical, values in configured.items():
        items = values if isinstance(values, list) else [values]
        aliases.setdefault(str(canonical), []).extend(str(item) for item in items if item)
    return aliases


def _matched_canonical_values(term: str, aliases: dict[str, list[str]]) -> set[str]:
    if not term:
        return set()
    matches: set[str] = set()
    for canonical, values in aliases.items():
        candidates = [canonical, *values]
        if any(_contains_phrase(term, candidate) for candidate in candidates):
            matches.add(canonical)
    return matches


def _contains_phrase(term: str, phrase: str) -> bool:
    normalized_phrase = _normalize_term(phrase)
    if not normalized_phrase:
        return False
    pattern = rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])"
    return re.search(pattern, term) is not None


def _normalize_term(value: str | None) -> str:
    if not value:
        return ""
    normalized = str(value).strip().lower().replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", normalized)


def _round_score(value: Any) -> float | None:
    if value is None:
        return None
    rounded = round(float(value), 2)
    if rounded.is_integer():
        return int(rounded)
    return rounded
