from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_RECT_SIZE_PATTERN = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|['’′])?\s*"
    r"(?:x|×|by)\s*(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|['’′])?(?![\d.])",
    re.IGNORECASE,
)
_ROUND_DIAMETER_PATTERN = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|['’′])?\s*"
    r"(?:round|circle|circular|oval)(?![a-z])",
    re.IGNORECASE,
)
_ROUND_MARKER = re.compile(r"\b(?:round|circle|circular|oval)\b", re.IGNORECASE)


@dataclass(frozen=True)
class RugSizeClassification:
    normalized_size: str | None
    rug_type: str | None
    analysis_threshold_profile: str | None
    reason: str


def classify_rug_size(
    size_spec: str | None,
    shape: str | None = None,
    mapping: dict[str, Any] | None = None,
) -> RugSizeClassification:
    if not size_spec:
        return RugSizeClassification(None, None, None, "产品信息缺失：目标推广尺寸")

    size_text = str(size_spec).strip().lower()
    shape_text = str(shape or "").strip().lower()
    if _ROUND_MARKER.search(size_text) or _ROUND_MARKER.search(shape_text):
        diameter = _extract_round_diameter(size_text)
        if diameter is None:
            dimensions = _extract_rect_dimensions(size_text)
            diameter = dimensions[0] if dimensions and dimensions[0] == dimensions[1] else None
        normalized = f"{_format_dimension(diameter)}ft round" if diameter is not None else size_text
        return RugSizeClassification(
            normalized,
            "round",
            None,
            "尺寸或形状含圆形标记，优先识别为圆形；圆形分析阈值待配置",
        )

    dimensions = _extract_rect_dimensions(size_text)
    if dimensions is None:
        return RugSizeClassification(size_text or None, None, None, "目标尺寸无法标准化")

    width, length = dimensions
    normalized = f"{_format_dimension(width)}x{_format_dimension(length)}"
    configured = mapping or {}
    runner_sizes = _configured_sizes(configured, "runner_sizes")
    doormat_sizes = _configured_sizes(configured, "doormat_sizes")
    area_sizes = _configured_sizes(configured, "area_sizes")
    runner_widths = _configured_numbers(configured, "runner_short_widths")

    if width in runner_widths and length > width:
        return RugSizeClassification(
            normalized,
            "runner",
            "runner",
            f"标准化短边为 {_format_dimension(width)}，按用户固定规则识别为长条",
        )
    if normalized in runner_sizes:
        return RugSizeClassification(normalized, "runner", "runner", "尺寸命中长条固定映射")
    if normalized in doormat_sizes:
        return RugSizeClassification(normalized, "doormat", "doormat", "尺寸命中门垫固定映射")
    if normalized in area_sizes:
        area_sq_ft = _area_in_square_feet(size_text, width, length)
        area_boundary_value = configured.get("area_small_max_square_feet")
        if area_boundary_value is None:
            return RugSizeClassification(
                normalized,
                "area_rug",
                None,
                "规则缺失：rug_size_type_mapping.area_small_max_square_feet",
            )
        area_boundary = float(area_boundary_value)
        profile = "area_small" if area_sq_ft <= area_boundary else "area_large"
        return RugSizeClassification(
            normalized,
            "area_rug",
            profile,
            f"尺寸命中区域固定映射，面积 {area_sq_ft:.2f} 平方英尺，调用 {profile} 阈值",
        )
    return RugSizeClassification(normalized, None, None, "尺寸未命中当前 Rug 尺寸类型映射")


def normalize_rug_type(value: str | None) -> str | None:
    if not value:
        return None
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "area": "area_rug",
        "area_rug": "area_rug",
        "区域": "area_rug",
        "区域地毯": "area_rug",
        "runner": "runner",
        "runner_rug": "runner",
        "长条": "runner",
        "长条地毯": "runner",
        "doormat": "doormat",
        "door_mat": "doormat",
        "室内进门垫": "doormat",
        "门垫": "doormat",
        "round": "round",
        "round_rug": "round",
        "圆形": "round",
        "圆形地毯": "round",
    }
    return aliases.get(normalized, normalized)


def _extract_rect_dimensions(value: str) -> tuple[float, float] | None:
    match = _RECT_SIZE_PATTERN.search(value)
    if not match:
        return None
    first, second = sorted((float(match.group(1)), float(match.group(2))))
    return first, second


def _extract_round_diameter(value: str) -> float | None:
    match = _ROUND_DIAMETER_PATTERN.search(value)
    if match:
        return float(match.group(1))
    number = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)(?![\d.])", value)
    return float(number.group(1)) if number else None


def _area_in_square_feet(source: str, width: float, length: float) -> float:
    if re.search(r"\b(?:in|inch|inches)\b|\"", source, re.IGNORECASE):
        return width * length / 144
    if re.search(r"\bcm\b", source, re.IGNORECASE):
        return width * length / (30.48 * 30.48)
    return width * length


def _configured_sizes(mapping: dict[str, Any], key: str) -> set[str]:
    values = mapping.get(key, []) or []
    return {str(value).strip().lower().replace(" ", "") for value in values if value}


def _configured_numbers(mapping: dict[str, Any], key: str) -> set[float]:
    values = mapping.get(key, []) or []
    return {float(value) for value in values}


def _format_dimension(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")
