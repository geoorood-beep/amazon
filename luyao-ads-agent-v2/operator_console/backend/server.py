from __future__ import annotations

from datetime import datetime, timezone
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import traceback
from typing import Any
from urllib.parse import quote, unquote, urlparse
import uuid

from openpyxl import load_workbook

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from validator import validate_operator_result
from agents_context import (
    build_agents_analysis_context,
    build_tool_receipt,
    canonical_digest,
    source_record,
)
from plan_exporter import export_new_product_architecture, export_sp_optimization_plan
from table_recognizer import SUPPORTED_EXTENSIONS, load_catalog, metadata_candidates, scan_report_file, summarize_upload


ROOT = Path(__file__).resolve().parents[2]
CONSOLE_ROOT = ROOT / "operator_console"
INTENTS_PATH = ROOT / "config/operator_intents.json"
CATALOG_PATH = ROOT / "config/operator_catalog.json"
MONITOR_CONFIG_PATH = ROOT / "config/threshold_monitoring.json"
RESULT_SCHEMA = CONSOLE_ROOT / "contracts/operator-result.schema.json"
JOBS_ROOT = ROOT / "runtime/operator-jobs"
UPLOADS_ROOT = ROOT / "runtime/operator-uploads"
PYTHON = ROOT / ".venv/bin/python"
CODEX = shutil.which("codex") or "/Applications/ChatGPT.app/Contents/Resources/codex"
MAX_JSON_BODY_BYTES = 2 * 1024 * 1024
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_MANUAL_PRODUCTS = 10
MAX_IMPORTED_PRODUCTS = 100
UPLOAD_ROLES = {"new_product", "reports"}
UPLOAD_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{8,80}")
WORKER_LOCK = threading.Lock()
ALLOWED_INPUT_ROOTS = tuple(
    path.resolve()
    for path in (ROOT, Path.home() / "Downloads", Path.home() / "Documents", Path.home() / "Desktop")
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def safe_input_path(raw: Any, *, required_file: bool = False) -> Path:
    text = str(raw or "").strip()
    if not text or len(text) > 1024:
        raise ValueError("路径为空或过长")
    path = Path(text).expanduser().resolve()
    if not any(path == root or root in path.parents for root in ALLOWED_INPUT_ROOTS):
        raise ValueError("只允许读取项目目录、Downloads、Documents或Desktop中的文件")
    if required_file and not path.is_file():
        raise ValueError(f"文件不存在: {path}")
    if not required_file and not path.is_dir():
        raise ValueError(f"目录不存在: {path}")
    return path


def safe_upload_root(upload_id: str) -> Path:
    if not UPLOAD_ID_PATTERN.fullmatch(upload_id):
        raise ValueError("upload_id无效")
    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    path = (UPLOADS_ROOT / upload_id).resolve()
    if UPLOADS_ROOT.resolve() not in path.parents:
        raise ValueError("upload_id越界")
    return path


def safe_upload_name(raw: str) -> str:
    name = unquote(raw or "").strip()
    if not name or len(name) > 240 or name != Path(name).name or "/" in name or "\\" in name or "\x00" in name:
        raise ValueError("文件名无效")
    if Path(name).suffix.casefold() not in SUPPORTED_EXTENSIONS:
        raise ValueError("只支持 XLSX、XLSM、CSV、TSV 表格")
    return name


def artifact_content_disposition(name: str) -> str:
    """Return an RFC 5987 filename header that remains latin-1 encodable."""

    suffix = Path(name).suffix.casefold()
    fallback = f"artifact{suffix}" if suffix else "artifact-download"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(name, safe='')}"


def requested_asins(fields: dict[str, Any]) -> list[str]:
    text = " ".join(str(fields.get(key) or "") for key in ("asin", "asins"))
    result: list[str] = []
    for asin in re.findall(r"\bB0[A-Z0-9]{8}\b", text.upper()):
        if asin not in result:
            result.append(asin)
    return result


def report_metadata(source: Path, old_workbook: Path | None = None) -> dict[str, Any]:
    source_asins: set[str] = set()
    workbook_asins: set[str] = set()
    source_dates: list[str] = []
    all_dates: list[str] = []
    issues: list[str] = []
    paths = [
        path for path in sorted(source.rglob("*"))
        if path.is_file() and path.suffix.casefold() in SUPPORTED_EXTENSIONS
    ]
    scan_paths = metadata_candidates(paths)
    if old_workbook is not None:
        scan_paths.append(old_workbook)
    for path in scan_paths:
        try:
            scan = scan_report_file(path)
            target = workbook_asins if old_workbook is not None and path == old_workbook else source_asins
            target.update(scan["asins"])
            values = [value for value in (scan["period_start"], scan["period_end"]) if value]
            all_dates.extend(values)
            if path != old_workbook:
                source_dates.extend(values)
        except Exception as exc:
            issues.append(f"{path.name}: {exc}")
    return {
        "asins": sorted(source_asins | workbook_asins),
        "source_asins": sorted(source_asins),
        "workbook_asins": sorted(workbook_asins),
        "suggested_asins": sorted(workbook_asins or source_asins),
        "period_start": min(all_dates) if all_dates else None,
        "period_end": max(all_dates) if all_dates else None,
        "source_period_start": min(source_dates) if source_dates else None,
        "source_period_end": max(source_dates) if source_dates else None,
        "issues": issues,
        "file_count": len(paths) + (1 if old_workbook else 0),
    }


def has_complete_overlap_windows(source: Path) -> bool:
    families = {"SP搜索词-按词", "SP投放对象报告", "SP广告位报告", "SP广告商品报告"}
    pattern = re.compile(r"^(?P<family>.+?)-(?P<grain>每日明细|汇总)-近(?P<days>7|14|30)天\.xlsx$")
    found: set[tuple[str, str, int]] = set()
    for path in source.glob("*.xlsx"):
        match = pattern.match(path.name)
        if match and match.group("family") in families:
            found.add((match.group("family"), match.group("grain"), int(match.group("days"))))
    expected = {
        (family, grain, days)
        for family in families
        for grain in ("每日明细", "汇总")
        for days in (7, 14, 30)
    }
    return expected <= found


def update_job(job_dir: Path, **changes: Any) -> dict[str, Any]:
    path = job_dir / "status.json"
    status = read_json(path)
    status.update(changes)
    status["updated_at"] = now_iso()
    write_json(path, status)
    return status


def run_command(command: list[str], log_path: Path, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    log_path.write_text(
        "COMMAND: " + " ".join(command[:3]) + " ...\n\nSTDOUT\n"
        + completed.stdout
        + "\nSTDERR\n"
        + completed.stderr,
        encoding="utf-8",
    )
    return completed


def command_issue(completed: subprocess.CompletedProcess[str], fallback: str, limit: int = 3000) -> str:
    """Keep the actionable process output and suppress a known non-fatal XLSX style warning."""

    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    lines = [
        line
        for line in combined.splitlines()
        if "Workbook contains no default style" not in line
        and "warn(\"Workbook contains no default style" not in line
    ]
    cleaned = "\n".join(lines).strip()
    return (cleaned or fallback)[-limit:]


def routing_entry(request: dict[str, Any], key: str, suffix: str) -> Path:
    values = request.get("routing", {}).get(key) or []
    for value in values:
        if str(value).endswith(suffix):
            path = (ROOT / str(value)).resolve()
            if path.exists() and (path == ROOT or ROOT in path.parents):
                return path
    raise ValueError(f"AGENTS路由未找到数据源: {suffix}")


def workbook_summary(path: Path, limit: int = 20) -> dict[str, Any]:
    workbook = load_workbook(path, data_only=False, read_only=True)
    sheets = []
    for sheet in workbook.worksheets:
        raw_rows = [[value for value in row] for row in sheet.iter_rows(values_only=True)]
        rows: list[list[Any]] = []
        notes: list[dict[str, str]] = []
        index = 0
        while index < len(raw_rows):
            row = raw_rows[index]
            first = str(row[0] or "").strip() if row else ""
            if first == "判断依据与设计逻辑":
                asin = str(row[1] or "").strip() if len(row) > 1 else ""
                content = ""
                if index + 1 < len(raw_rows):
                    content = str(raw_rows[index + 1][0] or "").strip()
                notes.append({"asin": asin, "title": first, "content": content})
                index += 2
                continue
            if any(value is not None and str(value).strip() for value in row):
                rows.append(row)
            index += 1
        sheets.append(
            {
                "name": sheet.title,
                "max_row": sheet.max_row,
                "data_row_count": max(0, len(rows) - 1),
                "preview": rows[:limit],
                "notes": notes,
            }
        )
    return {"path": str(path), "sheets": sheets}


def missing_fields(request: dict[str, Any], intent_config: dict[str, Any]) -> list[str]:
    fields = request.get("fields", {})
    if request.get("intent") == "NEW_PRODUCT_PROMOTION" and fields.get("products_json"):
        return []
    return [name for name in intent_config["required_fields"] if fields.get(name) in (None, "", [])]


def new_product_payloads(fields: dict[str, Any]) -> list[dict[str, Any]]:
    raw_json = fields.get("products_json")
    if raw_json:
        try:
            raw_products = json.loads(str(raw_json))
        except json.JSONDecodeError as exc:
            raise ValueError(f"产品清单JSON无效: {exc.msg}") from exc
        if not isinstance(raw_products, list):
            raise ValueError("产品清单必须是数组")
    else:
        raw_products = [fields]

    input_mode = str(fields.get("input_mode") or "manual")
    limit = MAX_MANUAL_PRODUCTS if input_mode == "manual" else MAX_IMPORTED_PRODUCTS
    if not raw_products:
        raise ValueError("产品清单为空")
    if len(raw_products) > limit:
        if input_mode == "manual":
            raise ValueError("手动录入最多10个ASIN；超过10个请使用表格上传")
        raise ValueError(f"单次表格导入最多{MAX_IMPORTED_PRODUCTS}个ASIN，请拆分批次")

    products: list[dict[str, Any]] = []
    seen_asins: set[str] = set()
    issues: list[str] = []
    for index, raw in enumerate(raw_products, start=1):
        if not isinstance(raw, dict):
            issues.append(f"第{index}条产品信息不是对象")
            continue
        asin = str(raw.get("asin") or "").strip().upper()
        marketplace = str(raw.get("marketplace") or fields.get("marketplace") or "US").strip().upper()
        missing = [
            label for label, value in (
                ("ASIN", asin),
                ("站点", marketplace),
                ("尺寸", raw.get("size_spec")),
                ("地毯类型", raw.get("rug_type")),
                ("日订单目标", raw.get("order_target_daily")),
            ) if value in (None, "")
        ]
        if missing:
            issues.append(f"第{index}条缺少: {', '.join(missing)}")
            continue
        if not re.fullmatch(r"B0[A-Z0-9]{8}", asin):
            issues.append(f"第{index}条ASIN格式无效: {asin or '空'}")
            continue
        if asin in seen_asins:
            issues.append(f"第{index}条ASIN重复: {asin}")
            continue
        try:
            order_target = float(raw.get("order_target_daily"))
            target_cpa = float(raw["target_cpa"]) if raw.get("target_cpa") not in (None, "") else None
            daily_budget = float(raw["daily_budget"]) if raw.get("daily_budget") not in (None, "") else None
        except (TypeError, ValueError):
            issues.append(f"第{index}条的日订单目标、CPA或预算不是有效数字")
            continue
        if order_target <= 0:
            issues.append(f"第{index}条日订单目标必须大于0")
            continue
        seen_asins.add(asin)
        scene_tags = [item.strip() for item in str(raw.get("scene_tags") or "").split(",") if item.strip()]
        products.append({
            "asin": asin,
            "sku": str(raw.get("sku") or asin),
            "category": "Rugs",
            "rug_type": raw.get("rug_type") or None,
            "scene_tags": scene_tags,
            "region_tags": scene_tags,
            "size_spec": raw.get("size_spec"),
            "material": raw.get("material") or None,
            "style": raw.get("style") or None,
            "color": raw.get("color") or None,
            "shape": raw.get("shape") or None,
            "order_target_daily": order_target,
            "target_cpa": target_cpa,
            "product_stage": "new_test",
            "operator_name": raw.get("operator_name") or fields.get("operator_name") or "web-operator",
            "requested_daily_budget": daily_budget,
            "marketplace": marketplace,
        })
    if issues:
        raise ValueError("；".join(issues[:20]))
    return products


def evidence_source_files(source: Path) -> list[Path]:
    """Return real operator evidence files; README and hidden files are not evidence."""
    allowed_suffixes = {".csv", ".xlsx", ".xlsm"}
    if source.is_file():
        return [source] if source.suffix.lower() in allowed_suffixes else []
    if not source.is_dir():
        return []
    return sorted(
        path
        for path in source.rglob("*")
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in allowed_suffixes
    )


def preprocess_new_product(request: dict[str, Any], job_dir: Path) -> dict[str, Any]:
    fields = request["fields"]
    artifacts = job_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    try:
        products = new_product_payloads(fields)
    except ValueError as exc:
        return {"status": "DATA_BLOCKED", "issues": [str(exc)], "artifacts": []}
    product_path = job_dir / "product.json"
    write_json(product_path, {"products": products})
    output_path = artifacts / "新品候选证据包.xlsx"
    try:
        aba_source = routing_entry(request, "knowledge_entries", "reference/rug-aba")
        history_source = routing_entry(
            request,
            "knowledge_entries",
            "20260707_rug_historical_search_terms_normalized.xlsx",
        )
        relevance_source = routing_entry(request, "knowledge_entries", "reference/rug-relevance")
        search_volume_source = routing_entry(
            request, "knowledge_entries", "reference/rug-search-volume"
        )
        module_cli = routing_entry(request, "tool_entries", "new_product_module/cli.py")
    except ValueError as exc:
        return {"status": "DATA_BLOCKED", "issues": [str(exc)], "artifacts": []}
    command = [
        str(PYTHON),
        str(module_cli),
        "--product",
        str(product_path),
        "--aba",
        str(aba_source),
        "--history",
        str(history_source),
        "--relevance",
        str(relevance_source),
        "--search-volume",
        str(search_volume_source),
        "--rules",
        str(ROOT / "new_product_module/config/category_rules.example.yaml"),
        "--output",
        str(output_path),
    ]
    completed = run_command(command, job_dir / "preprocess.log")
    if completed.returncode != 0:
        return {
            "status": "DATA_BLOCKED",
            "issues": [command_issue(completed, "广告架构预处理失败", 3000)],
            "artifacts": [],
        }
    evidence_issues: list[str] = []
    relevance_files = evidence_source_files(relevance_source)
    search_volume_files = evidence_source_files(search_volume_source)
    if not relevance_files:
        evidence_issues.append("请补充新品相关性表；缺少相关性证据时不会生成词组或广泛投放")
    if not search_volume_files:
        evidence_issues.append("请补充搜索词月搜索量表；缺少词根月搜索量时不会生成词组或广泛投放")
    return {
        "status": "READY_FOR_ANALYSIS",
        "mode": "NEW_PRODUCT_BATCH_MODULE" if len(products) > 1 else "NEW_PRODUCT_MODULE",
        "input_mode": str(fields.get("input_mode") or "manual"),
        "analysis_asins": [str(product["asin"]) for product in products],
        "product_count": len(products),
        "input_artifacts": [str(product_path)],
        "artifacts": [str(output_path)],
        "workbook_summary": workbook_summary(output_path),
        "match_type_data_status": "READY" if not evidence_issues else "PENDING_SOURCE",
        "relevance_source_count": len(relevance_files),
        "search_volume_source_count": len(search_volume_files),
        "issues": evidence_issues,
    }


def build_report_context(
    fields: dict[str, Any],
    job_dir: Path,
    period_start: str,
    period_end: str,
    asins: list[str],
) -> Path:
    link_id = ",".join(asins) if 0 < len(asins) <= 20 else f"AUTO_DETECTED_{len(asins)}_ASINS"
    context = {
        "schema_version": "1.0",
        "category": "rug",
        "marketplace": fields.get("marketplace") or "US",
        "account_id": fields.get("account_id") or "WEB_OPERATOR_UNCONFIRMED",
        "link_id": link_id if asins else "AUTO_DETECTED_REPORT_SCOPE",
        "timezone": fields.get("timezone") or "America/Los_Angeles",
        "currency": fields.get("currency") or "USD",
        "attribution_window_days": int(fields.get("attribution_window_days") or 7),
        "period_start": period_start,
        "period_end": period_end,
        "notes": "运营工作台从上传报表自动识别ASIN与日期；HUMAN_EXECUTION_ONLY",
    }
    path = job_dir / "ad_report_context.json"
    write_json(path, context)
    return path


def preprocess_reports(request: dict[str, Any], job_dir: Path) -> dict[str, Any]:
    fields = request["fields"]
    try:
        source = safe_input_path(fields.get("report_source_path"))
    except ValueError as exc:
        return {"status": "DATA_BLOCKED", "issues": [str(exc)], "artifacts": []}
    artifacts = job_dir / "artifacts/ad_analysis"
    artifacts.mkdir(parents=True, exist_ok=True)
    old_workbook = str(fields.get("old_product_workbook") or "").strip()
    workbook: Path | None = None
    if old_workbook:
        try:
            workbook = safe_input_path(old_workbook, required_file=True)
        except ValueError as exc:
            return {"status": "DATA_BLOCKED", "issues": [str(exc)], "artifacts": []}

    metadata = report_metadata(source, workbook)
    selected_asins = requested_asins(fields)
    if str(fields.get("asin") or "").strip() and not selected_asins:
        return {
            "status": "DATA_BLOCKED",
            "issues": ["ASIN格式无效；请输入10位、以B0开头的ASIN，多个ASIN用逗号或空格分隔"],
            "artifacts": [],
        }
    detected_asins = metadata["asins"]
    analysis_asins = selected_asins or metadata["suggested_asins"]
    if not metadata["period_start"] or not metadata["period_end"]:
        return {
            "status": "DATA_BLOCKED",
            "issues": ["上传表格中没有识别到日期列，无法自动确定分析周期"],
            "artifacts": [],
        }

    overlap_mode = has_complete_overlap_windows(source)
    if workbook is not None or overlap_mode:
        if len(analysis_asins) > 100:
            return {
                "status": "DATA_BLOCKED",
                "issues": [f"报表识别到{len(analysis_asins)}个ASIN，超过单任务100个上限；请在ASIN框选择需要分析的ASIN"],
                "artifacts": [],
            }
        if not analysis_asins:
            return {
                "status": "DATA_BLOCKED",
                "issues": ["上传表格中没有识别到ASIN；请在ASIN框输入一个或多个ASIN"],
                "artifacts": [],
            }
        successful_artifacts: list[str] = []
        packet_summaries: list[dict[str, Any]] = []
        issues = list(metadata["issues"])
        for asin in analysis_asins:
            asin_artifacts = artifacts / asin
            command = [
                str(PYTHON),
                str(ROOT / "scripts/build_name_keyed_ad_analysis.py"),
                "--source-dir",
                str(source),
                "--primary-asin",
                asin,
                "--output-dir",
                str(asin_artifacts),
            ]
            if workbook is not None:
                command[4:4] = ["--old-product-workbook", str(workbook)]
            log_path = job_dir / f"preprocess-{asin}.log"
            completed = run_command(command, log_path)
            expected_json = asin_artifacts / "ad_analysis_packet.json"
            expected_xlsx = asin_artifacts / "ad_analysis_packet.xlsx"
            if completed.returncode != 0 or not expected_json.is_file():
                issue = command_issue(completed, "聚合程序没有生成数据包", 3000)
                issues.append(f"{asin}: {issue}")
                continue
            packet = read_json(expected_json)
            successful_artifacts.append(str(expected_json))
            if expected_xlsx.exists():
                successful_artifacts.append(str(expected_xlsx))
            packet_summaries.append(
                {
                    key: packet.get(key)
                    for key in ("analysis_status", "execution_status", "category", "marketplace", "currency", "primary_asin", "issues", "metadata", "imported_issues")
                    if key in packet
                }
            )
        if not successful_artifacts:
            return {"status": "DATA_BLOCKED", "issues": issues or ["没有ASIN成功生成聚合结果"], "artifacts": []}
        return {
            "status": "READY_FOR_ANALYSIS",
            "mode": "NAME_KEYED_OVERLAP_SAFE_MULTI_ASIN" if workbook is not None else "REPORT_ONLY_OVERLAP_SAFE_MULTI_ASIN",
            "artifacts": successful_artifacts,
            "input_artifacts": [str(workbook)] if workbook is not None else [],
            "analysis_asins": [item.get("primary_asin") for item in packet_summaries],
            "detected_asins": detected_asins,
            "auto_period": {"start": metadata["period_start"], "end": metadata["period_end"]},
            "packet_summaries": packet_summaries,
            "issues": issues,
        }

    context = build_report_context(
        fields,
        job_dir,
        metadata["source_period_start"] or metadata["period_start"],
        metadata["source_period_end"] or metadata["period_end"],
        analysis_asins,
    )
    command = [
        str(PYTHON),
        str(ROOT / "scripts/build_ad_decision_packet.py"),
        "--source-dir",
        str(source),
        "--context",
        str(context),
        "--output-dir",
        str(artifacts),
    ]
    expected_json = artifacts / "ad_decision_packet.json"
    expected_xlsx = artifacts / "ad_decision_packet.xlsx"
    mode = "STANDARD_SIX_REPORTS_AUTO_SCOPE"
    completed = run_command(command, job_dir / "preprocess.log")
    if not expected_json.is_file():
        issue = command_issue(completed, "聚合程序没有生成数据包", 3000)
        return {"status": "DATA_BLOCKED", "issues": [issue, *metadata["issues"]], "artifacts": []}
    packet = read_json(expected_json)
    imported_issues = packet.get("imported_issues") or []
    blocking_issues = [
        str(item.get("message") or item.get("code") or item)
        for item in imported_issues
        if isinstance(item, dict) and item.get("blocking") is True
    ]
    if completed.returncode != 0 or blocking_issues:
        return {
            "status": "DATA_BLOCKED",
            "mode": "STANDARD_SIX_REPORTS_DQ_BLOCKED",
            "artifacts": [str(expected_json), str(expected_xlsx)] if expected_xlsx.exists() else [str(expected_json)],
            "analysis_asins": analysis_asins,
            "detected_asins": detected_asins,
            "auto_period": {"start": metadata["period_start"], "end": metadata["period_end"]},
            "packet_summary": {
                "metadata": packet.get("metadata"),
                "imported_issues": imported_issues,
            },
            "issues": blocking_issues
            or [command_issue(completed, "聚合数据质量未通过", 3000)],
        }
    return {
        "status": "READY_FOR_ANALYSIS",
        "mode": mode,
        "input_artifacts": [str(context)],
        "artifacts": [str(expected_json), str(expected_xlsx)] if expected_xlsx.exists() else [str(expected_json)],
        "analysis_asins": analysis_asins,
        "detected_asins": detected_asins,
        "auto_period": {"start": metadata["period_start"], "end": metadata["period_end"]},
        "packet_summary": {
            key: packet.get(key)
            for key in ("analysis_status", "execution_status", "category", "marketplace", "currency", "primary_asin", "issues", "metadata", "imported_issues")
            if key in packet
        },
        "issues": packet.get("issues") or packet.get("imported_issues") or metadata["issues"],
    }


def preprocess_weekly(request: dict[str, Any], job_dir: Path) -> dict[str, Any]:
    completed = run_command(
        [str(PYTHON), str(ROOT / "scripts/monitor_threshold_candidates.py")],
        job_dir / "preprocess.log",
    )
    status_path = ROOT / "outputs/threshold-calibration/latest/monitor_status.json"
    if completed.returncode != 0 or not status_path.is_file():
        return {"status": "DATA_BLOCKED", "issues": [(completed.stderr or completed.stdout)[-2000:]], "artifacts": []}
    artifacts = job_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    copied_status = artifacts / "weekly_threshold_monitor_status.json"
    shutil.copy2(status_path, copied_status)
    calibration_inputs = sorted(
        str(path)
        for path in (ROOT / "imports/threshold-calibration").glob("*.csv")
        if path.is_file()
    )
    return {
        "status": "READY_FOR_ANALYSIS",
        "mode": "WEEKLY_THRESHOLD_MONITOR",
        "monitor_status": read_json(status_path),
        "artifacts": [str(copied_status)],
        "input_artifacts": calibration_inputs,
        "issues": [],
    }


def preprocess(request: dict[str, Any], job_dir: Path) -> dict[str, Any]:
    if request["intent"] == "NEW_PRODUCT_PROMOTION":
        return preprocess_new_product(request, job_dir)
    if request["intent"] in {"OLD_PRODUCT_OPTIMIZATION", "AGGREGATE_REPORTS"}:
        return preprocess_reports(request, job_dir)
    if request["intent"] == "WEEKLY_REVIEW":
        return preprocess_weekly(request, job_dir)
    return {"status": "DATA_BLOCKED", "issues": ["未知任务意图"], "artifacts": []}


def codex_prompt(
    request_path: Path,
    preprocessing_path: Path,
    preprocessing: dict[str, Any],
    codex_run_id: str,
) -> str:
    context = preprocessing.get("agents_context") or {}
    required_sources = context.get("required_codex_sources") or []
    tool_receipt_ids = context.get("tool_receipt_ids") or []
    return f"""你是陆遥广告运营工作台的只读业务决策Worker。网页只是输入输出载体。
必须读取任务：{request_path}
必须读取预处理与AGENTS执行上下文：{preprocessing_path}
本次唯一允许的AGENTS上下文摘要：{context.get('context_digest')}
本次Codex运行ID：{codex_run_id}
必须逐项读取并在provenance.sources_read中原样返回以下完整清单，不得缺少、增加或改名：
{json.dumps(required_sources, ensure_ascii=False)}
必须在provenance.tool_receipt_ids中原样返回：{json.dumps(tool_receipt_ids, ensure_ascii=False)}
provenance固定为decision_engine=CODEX_AGENTS、codex_invoked=true、codex_run_id={codex_run_id}、agents_context_digest={context.get('context_digest')}。
只允许category=rug。不得使用执行上下文以外的规则、阈值、知识、工具、配置、合同或项目数据。
分析指标优先读取预处理JSON和工具输出证据；已有确定性聚合时不得再次逐行重算原始报表或ABA全库。
每条recommendation必须approval_required=true，并在evidence_sources中填写执行上下文sources内真实存在的精确path；不能只写泛化说明。
所有业务建议必须来自AGENTS八层规则。不得修改文件，不得连接或操作Amazon后台，不得补造Bid、预算、ID、阈值或数据。
NEW_PRODUCT_PROMOTION必须把最终广告架构写入new_product_architecture；网页和下载表只使用这里的行。每行必须绑定本次ASIN、匹配方式、投放对象和evidence_sources。数据不足时status=DATA_REQUIRED且数组为空。
其他意图的new_product_architecture固定为空数组。模型输出artifacts固定为空数组，最终文件只允许在Validator通过后由服务端渲染。
预处理含多个analysis_asins时必须逐ASIN给出可区分结论。证据不足时写入missing_inputs。
只返回符合operator_console/contracts/operator-result.schema.json的JSON，不要Markdown或代码围栏。job_id与intent必须完全一致。
safety固定execution_allowed=false、auto_apply=false、human_approval_required=true。"""


def fallback_result(request: dict[str, Any], preprocessing: dict[str, Any], reason: str) -> dict[str, Any]:
    blocked = preprocessing.get("status") == "DATA_BLOCKED"
    return {
        "schema_version": "1.0",
        "job_id": request["job_id"],
        "intent": request["intent"],
        "category": "rug",
        "status": "DATA_REQUIRED" if blocked else "CODEX_UNAVAILABLE",
        "title": "数据需要补齐" if blocked else "任务包已生成，等待Codex分析",
        "executive_summary": reason,
        "primary_issue": str((preprocessing.get("issues") or [reason])[0]),
        "recommendations": [],
        "new_product_architecture": [],
        "missing_inputs": [str(item) for item in preprocessing.get("issues", [])],
        "artifacts": [],
        "provenance": {
            "decision_engine": "NONE",
            "codex_invoked": False,
            "codex_run_id": None,
            "agents_context_digest": (preprocessing.get("agents_context") or {}).get("context_digest"),
            "sources_read": [],
            "tool_receipt_ids": [
                item.get("receipt_id")
                for item in preprocessing.get("tool_receipts", [])
                if isinstance(item, dict) and item.get("receipt_id")
            ],
        },
        "safety": {
            "execution_allowed": False,
            "auto_apply": False,
            "human_approval_required": True,
            "validator_status": "DATA_BLOCKED" if blocked else "CODEX_UNAVAILABLE",
        },
        "next_steps": ["补齐缺失资料后重新分析"] if blocked else ["确认Codex已登录后重新分析"],
    }


def parse_codex_result(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def analyze_with_codex(
    request: dict[str, Any], preprocessing: dict[str, Any], job_dir: Path
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if preprocessing.get("status") == "DATA_BLOCKED":
        return fallback_result(request, preprocessing, "确定性预处理未通过，未调用Codex生成广告建议。"), None
    output = job_dir / "codex_result.json"
    codex_run_id = f"{request['job_id']}-codex-{uuid.uuid4().hex[:12]}"
    prompt = codex_prompt(
        job_dir / "request.json",
        job_dir / "preprocessing.json",
        preprocessing,
        codex_run_id,
    )
    command = [
        CODEX,
        "exec",
        "-C",
        str(ROOT),
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--output-schema",
        str(RESULT_SCHEMA),
        "--output-last-message",
        str(output),
        prompt,
    ]
    completed = run_command(command, job_dir / "codex.log", timeout=1200)
    receipt: dict[str, Any] = {
        "schema_version": "2.1",
        "codex_run_id": codex_run_id,
        "codex_invoked": True,
        "status": "FAILED",
        "exit_code": completed.returncode,
        "prompt_sha256": canonical_digest(prompt),
        "agents_context_digest": (preprocessing.get("agents_context") or {}).get("context_digest"),
        "tool_receipt_ids": (preprocessing.get("agents_context") or {}).get("tool_receipt_ids", []),
        "output_path": str(output.resolve()),
        "output_sha256": None,
    }
    if completed.returncode != 0 or not output.is_file():
        receipt["receipt_id"] = canonical_digest(receipt)
        return fallback_result(request, preprocessing, "Codex Worker暂时不可用，任务包和预处理结果已保存。"), receipt
    try:
        result = parse_codex_result(output)
        write_json(output, result)
        receipt["status"] = "SUCCESS"
        receipt["output_sha256"] = source_record(
            ROOT, str(output.resolve()), "codex_output", external=True
        )["sha256"]
        receipt["receipt_id"] = canonical_digest(receipt)
        return result, receipt
    except Exception as exc:
        receipt["receipt_id"] = canonical_digest(receipt)
        return fallback_result(request, preprocessing, f"Codex输出无法通过JSON合同：{exc}"), receipt


def aggregation_only_result(request: dict[str, Any], preprocessing: dict[str, Any]) -> dict[str, Any]:
    if preprocessing.get("status") == "DATA_BLOCKED":
        return fallback_result(request, preprocessing, "Python聚合未通过，尚不能生成广告建议。")
    asins = [str(item) for item in preprocessing.get("analysis_asins", []) if item]
    period = preprocessing.get("auto_period") or {}
    asin_text = f"{len(asins)}个ASIN" if asins else "报表范围"
    period_text = (
        f"，数据范围 {period.get('start')} 至 {period.get('end')}"
        if period.get("start") and period.get("end")
        else ""
    )
    return {
        "schema_version": "1.0",
        "job_id": request["job_id"],
        "intent": request["intent"],
        "category": "rug",
        "status": "READY_FOR_HUMAN_REVIEW",
        "title": "广告报表聚合完成",
        "executive_summary": f"本地Python已完成{asin_text}的确定性聚合{period_text}。尚未调用Codex生成广告建议。",
        "primary_issue": None,
        "recommendations": [],
        "new_product_architecture": [],
        "missing_inputs": [],
        "artifacts": [str(item) for item in preprocessing.get("artifacts", [])],
        "provenance": {
            "decision_engine": "DETERMINISTIC_TOOL_ONLY",
            "codex_invoked": False,
            "codex_run_id": None,
            "agents_context_digest": (preprocessing.get("agents_context") or {}).get("context_digest"),
            "sources_read": [],
            "tool_receipt_ids": (preprocessing.get("agents_context") or {}).get("tool_receipt_ids", []),
        },
        "safety": {
            "execution_allowed": False,
            "auto_apply": False,
            "human_approval_required": True,
            "validator_status": "CANDIDATE_ONLY",
        },
        "next_steps": ["确认聚合结果后点击“生成 SP 广告优化方案”"],
    }


def attach_sp_plan_artifact(
    result: dict[str, Any],
    request: dict[str, Any],
    preprocessing: dict[str, Any],
    validation: dict[str, Any],
    job_dir: Path,
) -> dict[str, Any]:
    """Attach the final SP workbook only after the independent Validator passes."""

    if request.get("intent") != "OLD_PRODUCT_OPTIMIZATION":
        return result
    if validation.get("outcome") != "PASS_CANDIDATE_ONLY":
        return result
    output_path = job_dir / "artifacts" / "SP广告优化方案.xlsx"
    export_sp_optimization_plan(result, preprocessing, validation, output_path)
    result["artifacts"] = [str(output_path)]
    return result


def attach_new_product_artifact(
    result: dict[str, Any],
    request: dict[str, Any],
    preprocessing: dict[str, Any],
    validation: dict[str, Any],
    job_dir: Path,
) -> dict[str, Any]:
    if request.get("intent") != "NEW_PRODUCT_PROMOTION":
        return result
    if validation.get("outcome") != "PASS_CANDIDATE_ONLY":
        return result
    output_path = job_dir / "artifacts" / "广告架构设计方案.xlsx"
    export_new_product_architecture(result, preprocessing, validation, output_path)
    result["artifacts"] = [str(output_path)]
    return result


def final_artifact_receipts(paths: list[str]) -> list[dict[str, Any]]:
    return [
        source_record(ROOT, str(Path(path).resolve()), "final_artifact", external=True)
        for path in paths
    ]


def process_job(job_id: str) -> None:
    job_dir = JOBS_ROOT / job_id
    with WORKER_LOCK:
        try:
            request = read_json(job_dir / "request.json")
            intents = read_json(INTENTS_PATH)["intents"]
            missing = missing_fields(request, intents[request["intent"]])
            if missing:
                preprocessing = {"status": "DATA_BLOCKED", "issues": ["缺少必填字段: " + ", ".join(missing)], "artifacts": []}
            else:
                update_job(job_dir, status="PREPROCESSING", progress=20, message="正在整理数据")
                preprocessing = preprocess(request, job_dir)
            preprocessing["tool_receipts"] = (
                [build_tool_receipt(ROOT, request, preprocessing)]
                if preprocessing.get("status") == "READY_FOR_ANALYSIS"
                else []
            )
            agents_context = build_agents_analysis_context(ROOT, request, preprocessing)
            if preprocessing.get("status") == "READY_FOR_ANALYSIS" and agents_context.get("route_status") != "READY":
                preprocessing["status"] = "DATA_BLOCKED"
                preprocessing.setdefault("issues", []).append(
                    "AGENTS执行上下文未达到8/8或来源/工具回执校验失败"
                )
            context_path = job_dir / "agents_context.json"
            write_json(context_path, agents_context)
            preprocessing["agents_context"] = agents_context
            preprocessing["agents_context_path"] = str(context_path)
            write_json(job_dir / "preprocessing.json", preprocessing)
            aggregation_only = request["intent"] == "AGGREGATE_REPORTS" or (
                request["intent"] == "OLD_PRODUCT_OPTIMIZATION"
                and request.get("fields", {}).get("workflow_phase") == "AGGREGATE_ONLY"
            )
            if aggregation_only:
                result = aggregation_only_result(request, preprocessing)
                preprocessing["final_artifact_receipts"] = final_artifact_receipts(result.get("artifacts", []))
                write_json(job_dir / "preprocessing.json", preprocessing)
                write_json(job_dir / "result.json", result)
                update_job(job_dir, status="VALIDATING", progress=90, message="正在校验聚合结果")
                validation = validate_operator_result(
                    result, request, preprocessing, require_final_artifacts=True
                )
                write_json(job_dir / "validation.json", validation)
                ready = preprocessing.get("status") == "READY_FOR_ANALYSIS" and validation["outcome"] == "PASS_CANDIDATE_ONLY"
                if request["intent"] == "OLD_PRODUCT_OPTIMIZATION":
                    request["fields"]["workflow_phase"] = "AGGREGATED" if ready else "AGGREGATION_BLOCKED"
                    write_json(job_dir / "request.json", request)
                update_job(
                    job_dir,
                    status="COMPLETED" if ready else "BLOCKED",
                    progress=100,
                    message="聚合完成，等待生成建议" if ready else "聚合结果需要补充数据",
                    completed_at=now_iso(),
                )
                return
            update_job(job_dir, status="ANALYZING", progress=55, message="正在按AGENTS分析")
            result, codex_receipt = analyze_with_codex(request, preprocessing, job_dir)
            if codex_receipt is not None:
                preprocessing["codex_invocation_receipt"] = codex_receipt
                write_json(job_dir / "codex_invocation_receipt.json", codex_receipt)
            write_json(job_dir / "preprocessing.json", preprocessing)
            update_job(job_dir, status="VALIDATING", progress=85, message="正在进行安全校验")
            validation = validate_operator_result(result, request, preprocessing)
            result = attach_new_product_artifact(result, request, preprocessing, validation, job_dir)
            result = attach_sp_plan_artifact(result, request, preprocessing, validation, job_dir)
            require_final = request["intent"] in {"NEW_PRODUCT_PROMOTION", "OLD_PRODUCT_OPTIMIZATION"}
            if validation["outcome"] == "PASS_CANDIDATE_ONLY" and require_final:
                preprocessing["final_artifact_receipts"] = final_artifact_receipts(result.get("artifacts", []))
                validation = validate_operator_result(
                    result, request, preprocessing, require_final_artifacts=True
                )
            write_json(job_dir / "preprocessing.json", preprocessing)
            write_json(job_dir / "result.json", result)
            write_json(job_dir / "validation.json", validation)
            final_status = (
                "COMPLETED"
                if validation["outcome"] == "PASS_CANDIDATE_ONLY"
                and result.get("status") == "READY_FOR_HUMAN_REVIEW"
                else "BLOCKED"
            )
            update_job(
                job_dir,
                status=final_status,
                progress=100,
                message="等待人工确认" if final_status == "COMPLETED" else "Validator已阻断",
                completed_at=now_iso(),
            )
        except Exception as exc:
            (job_dir / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
            update_job(job_dir, status="FAILED", progress=100, message=str(exc), completed_at=now_iso())


def process_recommendations(job_id: str) -> None:
    job_dir = JOBS_ROOT / job_id
    with WORKER_LOCK:
        try:
            request = read_json(job_dir / "request.json")
            preprocessing = read_json(job_dir / "preprocessing.json")
            update_job(job_dir, status="ANALYZING", progress=60, message="正在生成 SP 广告优化方案")
            result, codex_receipt = analyze_with_codex(request, preprocessing, job_dir)
            if codex_receipt is not None:
                preprocessing["codex_invocation_receipt"] = codex_receipt
                write_json(job_dir / "codex_invocation_receipt.json", codex_receipt)
            write_json(job_dir / "preprocessing.json", preprocessing)
            update_job(job_dir, status="VALIDATING", progress=88, message="正在进行安全校验")
            validation = validate_operator_result(result, request, preprocessing)
            result = attach_sp_plan_artifact(result, request, preprocessing, validation, job_dir)
            if validation["outcome"] == "PASS_CANDIDATE_ONLY":
                preprocessing["final_artifact_receipts"] = final_artifact_receipts(result.get("artifacts", []))
                validation = validate_operator_result(
                    result, request, preprocessing, require_final_artifacts=True
                )
            write_json(job_dir / "preprocessing.json", preprocessing)
            write_json(job_dir / "result.json", result)
            write_json(job_dir / "validation.json", validation)
            final_status = (
                "COMPLETED"
                if validation["outcome"] == "PASS_CANDIDATE_ONLY"
                and result.get("status") == "READY_FOR_HUMAN_REVIEW"
                else "BLOCKED"
            )
            request["fields"]["workflow_phase"] = "ANALYZED" if final_status == "COMPLETED" else "ANALYSIS_BLOCKED"
            write_json(job_dir / "request.json", request)
            update_job(
                job_dir,
                status=final_status,
                progress=100,
                message="SP 广告优化方案已生成，等待人工确认" if final_status == "COMPLETED" else "Validator已阻断",
                completed_at=now_iso(),
            )
        except Exception as exc:
            (job_dir / "recommendation-error.log").write_text(traceback.format_exc(), encoding="utf-8")
            update_job(job_dir, status="FAILED", progress=100, message=str(exc), completed_at=now_iso())


def public_job(job_dir: Path) -> dict[str, Any]:
    status = read_json(job_dir / "status.json")
    request = read_json(job_dir / "request.json")
    payload: dict[str, Any] = {
        **status,
        "stage": status["status"],
        "intent": request["intent"],
        "request": request,
    }
    for name in ("preprocessing", "result", "validation"):
        path = job_dir / f"{name}.json"
        payload[name] = read_json(path) if path.is_file() else None
    return payload


class Handler(BaseHTTPRequestHandler):
    server_version = "LuyaoOperator/1.8"

    def end_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin in {"http://localhost:3001", "http://127.0.0.1:3001"}:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, X-Upload-Id, X-Upload-Role, X-File-Name",
        )
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("[operator] " + format % args + "\n")

    def json_response(self, value: Any, status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            schedule = read_json(MONITOR_CONFIG_PATH)["schedule"]
            self.json_response(
                {
                    "status": "READY",
                    "project": "陆遥广告智能体",
                    "version": "V2.1",
                    "ruleset_version": "V2.0",
                    "console_version": "V1.8",
                    "category": "rug",
                    "execution_boundary": "HUMAN_EXECUTION_ONLY",
                    "codex_worker_available": Path(CODEX).is_file() or shutil.which(CODEX) is not None,
                    "weekly_monitor": schedule,
                }
            )
            return
        if parsed.path == "/api/catalog":
            self.json_response(read_json(CATALOG_PATH))
            return
        upload_match = re.fullmatch(r"/api/uploads/([A-Za-z0-9-]+)/summary", parsed.path)
        if upload_match:
            try:
                upload_root = safe_upload_root(upload_match.group(1))
                if not upload_root.is_dir():
                    self.json_response({"error": "UPLOAD_NOT_FOUND"}, 404)
                    return
                self.json_response(summarize_upload(upload_root, load_catalog(CATALOG_PATH)))
            except ValueError as exc:
                self.json_response({"error": str(exc)}, 400)
            return
        if parsed.path == "/api/jobs":
            JOBS_ROOT.mkdir(parents=True, exist_ok=True)
            jobs = []
            for path in sorted(JOBS_ROOT.iterdir(), key=lambda item: item.name, reverse=True)[:20]:
                if path.is_dir() and (path / "status.json").is_file():
                    jobs.append(public_job(path))
            self.json_response({"jobs": jobs})
            return
        match = re.fullmatch(r"/api/jobs/([A-Za-z0-9-]+)", parsed.path)
        if match:
            job_dir = JOBS_ROOT / match.group(1)
            if not (job_dir / "status.json").is_file():
                self.json_response({"error": "JOB_NOT_FOUND"}, 404)
                return
            self.json_response(public_job(job_dir))
            return
        artifact = re.fullmatch(r"/api/jobs/([A-Za-z0-9-]+)/artifacts/(.+)", parsed.path)
        if artifact:
            job_dir = (JOBS_ROOT / artifact.group(1) / "artifacts").resolve()
            target = (job_dir / unquote(artifact.group(2))).resolve()
            if job_dir not in target.parents or not target.is_file():
                self.json_response({"error": "ARTIFACT_NOT_FOUND"}, 404)
                return
            body = target.read_bytes()
            self.send_response(200)
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", artifact_content_disposition(target.name))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.json_response({"error": "NOT_FOUND"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/uploads":
            self.handle_upload()
            return
        recommendation_match = re.fullmatch(r"/api/jobs/([A-Za-z0-9-]+)/recommendations", parsed.path)
        if recommendation_match:
            self.handle_recommendations(recommendation_match.group(1))
            return
        if parsed.path != "/api/jobs":
            self.json_response({"error": "NOT_FOUND"}, 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_JSON_BODY_BYTES:
            self.json_response({"error": "INVALID_BODY_SIZE"}, 400)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            intent = str(payload.get("intent") or "")
            intents = read_json(INTENTS_PATH)["intents"]
            if intent not in intents:
                raise ValueError("任务意图无效")
            fields = payload.get("fields")
            if not isinstance(fields, dict):
                raise ValueError("fields必须为对象")
            if any(
                len(str(value)) > (1024 * 1024 if key == "products_json" else 5000)
                for key, value in fields.items()
            ):
                raise ValueError("输入字段过长")
            job_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
            job_dir = JOBS_ROOT / job_id
            request = {
                "schema_version": "1.0",
                "job_id": job_id,
                "intent": intent,
                "category": "rug",
                "execution_boundary": "HUMAN_EXECUTION_ONLY",
                "created_at": now_iso(),
                "fields": fields,
                "routing": intents[intent],
            }
            write_json(job_dir / "request.json", request)
            write_json(
                job_dir / "status.json",
                {
                    "job_id": job_id,
                    "status": "QUEUED",
                    "progress": 5,
                    "message": "任务已创建",
                    "created_at": request["created_at"],
                    "updated_at": request["created_at"],
                },
            )
            threading.Thread(target=process_job, args=(job_id,), daemon=True).start()
            self.json_response(public_job(job_dir), 201)
        except (ValueError, json.JSONDecodeError) as exc:
            self.json_response({"error": str(exc)}, 400)

    def handle_recommendations(self, job_id: str) -> None:
        job_dir = JOBS_ROOT / job_id
        if not (job_dir / "status.json").is_file():
            self.json_response({"error": "JOB_NOT_FOUND"}, 404)
            return
        try:
            status = read_json(job_dir / "status.json")
            request = read_json(job_dir / "request.json")
            preprocessing = read_json(job_dir / "preprocessing.json")
            if status.get("status") != "COMPLETED":
                raise ValueError("聚合任务尚未完成")
            if request.get("intent") != "OLD_PRODUCT_OPTIMIZATION":
                raise ValueError("只有 SP 广告优化聚合任务可以继续生成方案")
            if request.get("fields", {}).get("workflow_phase") != "AGGREGATED":
                raise ValueError("任务不在等待生成建议状态")
            if preprocessing.get("status") != "READY_FOR_ANALYSIS":
                raise ValueError("聚合数据未达到分析条件")
            for source_name, target_name in (
                ("result.json", "aggregation_result.json"),
                ("validation.json", "aggregation_validation.json"),
            ):
                source = job_dir / source_name
                if source.is_file():
                    shutil.copy2(source, job_dir / target_name)
            request["fields"]["workflow_phase"] = "ANALYSIS_REQUESTED"
            request["fields"]["analysis_requested_at"] = now_iso()
            write_json(job_dir / "request.json", request)
            update_job(job_dir, status="QUEUED", progress=55, message="广告建议任务已创建")
            threading.Thread(target=process_recommendations, args=(job_id,), daemon=True).start()
            self.json_response(public_job(job_dir), 202)
        except (ValueError, OSError, KeyError) as exc:
            self.json_response({"error": str(exc)}, 409)

    def handle_upload(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_UPLOAD_BYTES:
                self.json_response({"error": "文件为空或超过200MB"}, 413)
                return
            role = str(self.headers.get("X-Upload-Role") or "").strip()
            if role not in UPLOAD_ROLES:
                raise ValueError("上传角色无效")
            name = safe_upload_name(str(self.headers.get("X-File-Name") or ""))
            upload_id = str(self.headers.get("X-Upload-Id") or "").strip()
            if upload_id:
                upload_root = safe_upload_root(upload_id)
            else:
                upload_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:12]
                upload_root = safe_upload_root(upload_id)
            role_dir = upload_root / role
            role_dir.mkdir(parents=True, exist_ok=True)
            if role == "new_product" and any(role_dir.iterdir()):
                self.json_response({"error": "此位置只允许上传一个表格，请重新选择任务后上传"}, 409)
                return
            target = role_dir / name
            if target.exists():
                self.json_response({"error": f"文件已上传: {name}"}, 409)
                return
            temporary = target.with_suffix(target.suffix + ".part")
            remaining = length
            with temporary.open("wb") as handle:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("上传内容提前结束")
                    handle.write(chunk)
                    remaining -= len(chunk)
            temporary.replace(target)
            self.json_response(
                {"upload_id": upload_id, "role": role, "name": name, "size": length},
                201,
            )
        except (ValueError, OSError) as exc:
            try:
                if "temporary" in locals() and temporary.exists():
                    temporary.unlink()
            except OSError:
                pass
            self.json_response({"error": str(exc)}, 400)


def main() -> int:
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)
    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 8766), Handler)
    print("陆遥广告运营台后台：http://127.0.0.1:8766")
    print("边界：Rug only / HUMAN_EXECUTION_ONLY")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
