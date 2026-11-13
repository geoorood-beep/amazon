from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from .schemas import CategoryRules


def load_rules(path: str | Path) -> CategoryRules:
    raw = Path(path).read_text(encoding="utf-8")
    data = _load_yaml_or_json(raw)
    return CategoryRules.model_validate(data)


def _load_yaml_or_json(raw: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(raw)
        if data is None:
            return {}
        return data
    except ModuleNotFoundError:
        return _parse_limited_yaml(raw)


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    result: list[str] = []
    for char in line:
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == "\\" and in_double:
            result.append(char)
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == "#" and not in_single and not in_double:
            break
        result.append(char)
    return "".join(result).rstrip()


def _parse_limited_yaml(raw: str) -> dict[str, Any]:
    cleaned = "\n".join(_strip_comment(line) for line in raw.splitlines())
    stripped = cleaned.strip()
    if stripped.startswith("{"):
        return json.loads(_remove_trailing_commas(stripped))

    lines: list[tuple[int, str]] = []
    for line in cleaned.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        lines.append((indent, line.strip()))
    value, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise ValueError(f"Could not parse rules file near line: {lines[index][1]}")
    if not isinstance(value, dict):
        raise ValueError("Rules file must contain a mapping at the top level")
    return value


def _remove_trailing_commas(text: str) -> str:
    while ",}" in text or ",]" in text:
        text = text.replace(",}", "}").replace(",]", "]")
    return text


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    current_indent, current = lines[index]
    if current_indent < indent:
        return {}, index
    if current.startswith("- "):
        return _parse_list(lines, index, current_indent)
    return _parse_mapping(lines, index, current_indent)


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    values: list[Any] = []
    while index < len(lines):
        current_indent, current = lines[index]
        if current_indent != indent or not current.startswith("- "):
            break
        item_text = current[2:].strip()
        index += 1
        if not item_text:
            item, index = _parse_block(lines, index, indent + 2)
            values.append(item)
            continue
        if _looks_like_key_value(item_text):
            item: dict[str, Any] = {}
            key, value = _split_key_value(item_text)
            item[key] = _parse_scalar(value) if value else None
            while index < len(lines) and lines[index][0] > indent:
                if lines[index][1].startswith("- "):
                    child, index = _parse_block(lines, index, lines[index][0])
                    values.append(child)
                    break
                child_indent = lines[index][0]
                child_map, index = _parse_mapping(lines, index, child_indent)
                item.update(child_map)
            else:
                values.append(item)
                continue
            if values and values[-1] is not item:
                continue
            values.append(item)
        else:
            values.append(_parse_scalar(item_text))
    return values, index


def _parse_mapping(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    mapping: dict[str, Any] = {}
    while index < len(lines):
        current_indent, current = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            break
        if current.startswith("- "):
            break
        key, value = _split_key_value(current)
        index += 1
        if value == "":
            if index < len(lines) and lines[index][0] > current_indent:
                child, index = _parse_block(lines, index, lines[index][0])
                mapping[key] = child
            else:
                mapping[key] = None
        else:
            mapping[key] = _parse_scalar(value)
    return mapping, index


def _looks_like_key_value(text: str) -> bool:
    return ":" in text and not text.startswith(("http://", "https://"))


def _split_key_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"Expected key/value line, got: {text}")
    key, value = text.split(":", 1)
    return key.strip().strip('"').strip("'"), value.strip()


def _parse_scalar(value: str) -> Any:
    if value == "":
        return ""
    lowered = value.lower()
    if lowered in {"null", "none", "~"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.startswith("[") or value.startswith("{"):
        pythonish = value.replace(": null", ": None")
        pythonish = pythonish.replace("[null", "[None")
        return ast.literal_eval(pythonish)
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return ast.literal_eval(value)
    number = value.replace(",", "")
    try:
        if "." in number:
            return float(number)
        return int(number)
    except ValueError:
        return value
