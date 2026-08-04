from __future__ import annotations

from datetime import datetime, timezone
import json
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
from urllib.parse import unquote, urlparse
import uuid

from openpyxl import load_workbook

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from validator import validate_operator_result
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


def workbook_summary(path: Path, limit: int = 20) -> dict[str, Any]:
    workbook = load_workbook(path, data_only=False, read_only=True)
    sheets = []
    for sheet in workbook.worksheets:
        rows = []
        for row in sheet.iter_rows(values_only=True, max_row=min(sheet.max_row, limit)):
            rows.append([value for value in row])
        sheets.append({"name": sheet.title, "max_row": sheet.max_row, "preview": rows})
    return {"path": str(path), "sheets": sheets}


def missing_fields(request: dict[str, Any], intent_config: dict[str, Any]) -> list[str]:
    fields = request.get("fields", {})
    return [name for name in intent_config["required_fields"] if fields.get(name) in (None, "", [])]


def preprocess_new_product(request: dict[str, Any], job_dir: Path) -> dict[str, Any]:
    fields = request["fields"]
    artifacts = job_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    product = {
        "asin": fields.get("asin"),
        "sku": fields.get("sku") or fields.get("asin"),
        "category": "Rugs",
        "rug_type": fields.get("rug_type") or None,
        "scene_tags": [item.strip() for item in str(fields.get("scene_tags") or "").split(",") if item.strip()],
        "region_tags": [item.strip() for item in str(fields.get("scene_tags") or "").split(",") if item.strip()],
        "size_spec": fields.get("size_spec"),
        "material": fields.get("material") or None,
        "style": fields.get("style") or None,
        "color": fields.get("color") or None,
        "shape": fields.get("shape") or None,
        "order_target_daily": float(fields.get("order_target_daily")),
        "target_cpa": float(fields["target_cpa"]) if fields.get("target_cpa") else None,
        "product_stage": "new_test",
        "operator_name": fields.get("operator_name") or "web-operator",
        "requested_daily_budget": float(fields["daily_budget"]) if fields.get("daily_budget") else None,
    }
    product_path = job_dir / "product.json"
    write_json(product_path, product)
    output_path = artifacts / "new_product_plan.xlsx"
    command = [
        str(PYTHON),
        str(ROOT / "new_product_module/cli.py"),
        "--product",
        str(product_path),
        "--aba",
        str(ROOT / "reference/rug-aba"),
        "--history",
        str(ROOT / "reference/category-history/rug/normalized/20260707_rug_historical_search_terms_normalized.xlsx"),
        "--rules",
        str(ROOT / "new_product_module/config/category_rules.example.yaml"),
        "--output",
        str(output_path),
    ]
    completed = run_command(command, job_dir / "preprocess.log")
    if completed.returncode != 0:
        return {"status": "DATA_BLOCKED", "issues": [completed.stderr[-2000:]], "artifacts": []}
    return {
        "status": "READY_FOR_ANALYSIS",
        "mode": "NEW_PRODUCT_MODULE",
        "artifacts": [str(output_path)],
        "workbook_summary": workbook_summary(output_path),
        "issues": [],
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
                issue = (completed.stderr or completed.stdout or "聚合程序没有生成数据包")[-2000:]
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
    if completed.returncode != 0 or not expected_json.is_file():
        issue = (completed.stderr or completed.stdout or "聚合程序没有生成数据包")[-3000:]
        return {"status": "DATA_BLOCKED", "issues": [issue, *metadata["issues"]], "artifacts": []}
    packet = read_json(expected_json)
    return {
        "status": "READY_FOR_ANALYSIS",
        "mode": mode,
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
    return {
        "status": "READY_FOR_ANALYSIS",
        "mode": "WEEKLY_THRESHOLD_MONITOR",
        "monitor_status": read_json(status_path),
        "artifacts": [str(copied_status)],
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


def codex_prompt(request_path: Path, preprocessing_path: Path) -> str:
    return f"""你是陆遥广告运营工作台的只读分析Worker。
必须先读取项目根AGENTS.md与config/project_scope.json，只允许category=rug。
读取任务：{request_path}
读取确定性预处理：{preprocessing_path}
按任务意图读取operator_intents中登记的规则、阈值和输出合同。不得修改任何文件，不得连接或操作Amazon后台。
预处理为DATA_BLOCKED时，status必须是DATA_REQUIRED或VALIDATOR_BLOCKED，不得给出可执行建议。
所有recommendations必须approval_required=true。safety固定execution_allowed=false、auto_apply=false、human_approval_required=true。
预处理含多个analysis_asins时，必须逐ASIN给出可区分的结论；每条动作和证据以[ASIN]开头，不得把不同ASIN合并成一个动作。
只返回符合operator_console/contracts/operator-result.schema.json的JSON，不要Markdown，不要代码围栏。
结果job_id与intent必须和任务完全一致。证据不足时明确列入missing_inputs，不得补造数字。"""


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
        "missing_inputs": [str(item) for item in preprocessing.get("issues", [])],
        "artifacts": [str(item) for item in preprocessing.get("artifacts", [])],
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


def analyze_with_codex(request: dict[str, Any], preprocessing: dict[str, Any], job_dir: Path) -> dict[str, Any]:
    if preprocessing.get("status") == "DATA_BLOCKED":
        return fallback_result(request, preprocessing, "确定性预处理未通过，未调用Codex生成广告建议。")
    output = job_dir / "codex_result.json"
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
        codex_prompt(job_dir / "request.json", job_dir / "preprocessing.json"),
    ]
    completed = run_command(command, job_dir / "codex.log", timeout=1200)
    if completed.returncode != 0 or not output.is_file():
        return fallback_result(request, preprocessing, "Codex Worker暂时不可用，任务包和预处理结果已保存。")
    try:
        return parse_codex_result(output)
    except Exception as exc:
        return fallback_result(request, preprocessing, f"Codex输出无法通过JSON合同：{exc}")


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
        "missing_inputs": [],
        "artifacts": [str(item) for item in preprocessing.get("artifacts", [])],
        "safety": {
            "execution_allowed": False,
            "auto_apply": False,
            "human_approval_required": True,
            "validator_status": "CANDIDATE_ONLY",
        },
        "next_steps": ["确认聚合结果后点击“生成广告建议方案”"],
    }


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
            write_json(job_dir / "preprocessing.json", preprocessing)
            aggregation_only = request["intent"] == "AGGREGATE_REPORTS" or (
                request["intent"] == "OLD_PRODUCT_OPTIMIZATION"
                and request.get("fields", {}).get("workflow_phase") == "AGGREGATE_ONLY"
            )
            if aggregation_only:
                result = aggregation_only_result(request, preprocessing)
                write_json(job_dir / "result.json", result)
                update_job(job_dir, status="VALIDATING", progress=90, message="正在校验聚合结果")
                validation = validate_operator_result(result, request, preprocessing)
                write_json(job_dir / "validation.json", validation)
                ready = preprocessing.get("status") == "READY_FOR_ANALYSIS" and validation["outcome"] == "PASS_CANDIDATE_ONLY"
                if request["intent"] == "OLD_PRODUCT_OPTIMIZATION":
                    request["fields"]["workflow_phase"] = "AGGREGATED" if ready else "AGGREGATION_BLOCKED"
                    write_json(job_dir / "request.json", request)
                update_job(
                    job_dir,
                    status="COMPLETED" if validation["outcome"] == "PASS_CANDIDATE_ONLY" else "BLOCKED",
                    progress=100,
                    message="聚合完成，等待生成建议" if ready else "聚合结果需要补充数据",
                    completed_at=now_iso(),
                )
                return
            update_job(job_dir, status="ANALYZING", progress=55, message="正在按AGENTS分析")
            result = analyze_with_codex(request, preprocessing, job_dir)
            result["artifacts"] = [str(item) for item in preprocessing.get("artifacts", [])]
            write_json(job_dir / "result.json", result)
            update_job(job_dir, status="VALIDATING", progress=85, message="正在进行安全校验")
            validation = validate_operator_result(result, request, preprocessing)
            write_json(job_dir / "validation.json", validation)
            final_status = "COMPLETED" if validation["outcome"] == "PASS_CANDIDATE_ONLY" else "BLOCKED"
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
            update_job(job_dir, status="ANALYZING", progress=60, message="正在生成广告建议方案")
            result = analyze_with_codex(request, preprocessing, job_dir)
            result["artifacts"] = [str(item) for item in preprocessing.get("artifacts", [])]
            write_json(job_dir / "result.json", result)
            update_job(job_dir, status="VALIDATING", progress=88, message="正在进行安全校验")
            validation = validate_operator_result(result, request, preprocessing)
            write_json(job_dir / "validation.json", validation)
            final_status = "COMPLETED" if validation["outcome"] == "PASS_CANDIDATE_ONLY" else "BLOCKED"
            request["fields"]["workflow_phase"] = "ANALYZED" if final_status == "COMPLETED" else "ANALYSIS_BLOCKED"
            write_json(job_dir / "request.json", request)
            update_job(
                job_dir,
                status=final_status,
                progress=100,
                message="广告建议已生成，等待人工确认" if final_status == "COMPLETED" else "Validator已阻断",
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
    server_version = "LuyaoOperator/1.2"

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
                    "version": "V2.0",
                    "console_version": "V1.3",
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
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
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
            if any(len(str(value)) > 5000 for value in fields.values()):
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
                raise ValueError("只有老品优化聚合任务可以继续生成建议")
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
