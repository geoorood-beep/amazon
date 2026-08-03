#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/connectors.example.yaml"
PLACEHOLDER = "PLACEHOLDER_NOT_ACTIVE"
REQUIRED_DOCS = (
    "integrations/external-integration-gateway.md",
    "integrations/mcp/mcp-connection-slot.md",
    "integrations/api/http-api-webhook-slot.md",
    "integrations/server/external-server-slot.md",
    "integrations/ingestion/ingestion-pipeline-slot.md",
    "integrations/cloud/threshold-monitoring-cloud-slot.md",
    "contracts/external-ingest.md",
)
ENV_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED_DOCS:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"缺少外部接入预留文件：{relative}")
            continue
        if PLACEHOLDER not in path.read_text(encoding="utf-8"):
            errors.append(f"外部接入预留文件未保持占位状态：{relative}")

    if not CONFIG_PATH.is_file():
        errors.append("缺少连接器禁用模板：config/connectors.example.yaml")
    else:
        config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        if config.get("slot_status") != PLACEHOLDER:
            errors.append("连接器总状态必须保持 PLACEHOLDER_NOT_ACTIVE")

        global_config = config.get("global", {})
        required_global = {
            "enabled": False,
            "receive_only": True,
            "allow_external_rule_changes": False,
            "allow_action_execution": False,
        }
        for key, expected in required_global.items():
            if global_config.get(key) is not expected:
                errors.append(f"连接器 global.{key} 必须为 {expected}")
        if global_config.get("allowed_categories") != ["rug"]:
            errors.append("连接器允许类目必须且只能为 rug")

        connectors = config.get("connectors")
        expected_connectors = {
            "mcp",
            "external_api",
            "inbound_api",
            "external_server",
            "cloud_storage",
            "cloud_runner",
        }
        if not isinstance(connectors, dict) or set(connectors) != expected_connectors:
            errors.append(
                "连接器占位项必须完整登记 mcp/external_api/inbound_api/"
                "external_server/cloud_storage/cloud_runner"
            )
        else:
            for name, connector in connectors.items():
                if connector.get("enabled") is not False:
                    errors.append(f"连接器 {name} 必须保持 disabled")
                if connector.get("implementation_status") != PLACEHOLDER:
                    errors.append(f"连接器 {name} 必须保持占位状态")
                for key, value in connector.items():
                    if not key.endswith("_env"):
                        continue
                    if not isinstance(value, str) or not ENV_NAME_PATTERN.fullmatch(value):
                        errors.append(f"连接器 {name}.{key} 必须只登记合法环境变量名")

        raw_config = CONFIG_PATH.read_text(encoding="utf-8")
        if "http://" in raw_config or "https://" in raw_config:
            errors.append("占位配置不得写入真实或猜测的 Endpoint")

    if errors:
        print("第 05 层外部接入占位校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "第 05 层外部接入占位校验通过："
        "MCP/API/外部服务器/云存储/云端任务均为 PLACEHOLDER_NOT_ACTIVE，"
        "只接收边界、Rug 范围和禁止执行门保持有效。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
