#!/usr/bin/env python3
"""Download weekly Amazon ad report attachments and prepare an AGENTS analysis run.

This script intentionally does not store mailbox credentials in the repository.
Credentials are read from environment variables declared in the JSON config.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import email
from email.header import make_header, decode_header
import hashlib
import imaplib
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import sys
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "weekly_amazon_report_ingest.json"
DEFAULT_SAVE_ROOT = PROJECT_ROOT / "imports" / "amazon_ads_weekly"

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv", ".zip"}

REPORT_RULES = [
    {
        "id": "sp_search_terms_daily",
        "standard_name": "SP搜索词-按词-每日明细",
        "required": True,
        "patterns": [
            "搜索词-按词-每日",
            "搜索词每日",
            "search term daily",
            "search terms daily",
            "search-term-daily",
            "search_terms_daily",
            "daily search term",
            "按词每日明细",
        ],
    },
    {
        "id": "sp_search_terms_summary",
        "standard_name": "SP搜索词-按词-汇总",
        "required": True,
        "patterns": [
            "搜索词-按词-汇总",
            "搜索词汇总",
            "search term summary",
            "search terms summary",
            "search-term-summary",
            "search_terms_summary",
            "summary search term",
            "按词汇总",
        ],
    },
    {
        "id": "sp_targeting",
        "standard_name": "SP投放对象 / 关键词 / 商品投放报告",
        "required": True,
        "patterns": [
            "投放对象",
            "关键词报告",
            "商品投放",
            "targeting report",
            "targeting",
            "keyword report",
            "keywords report",
            "product targeting",
            "sponsored products targeting",
        ],
    },
    {
        "id": "sp_placement",
        "standard_name": "SP广告位报告",
        "required": True,
        "patterns": [
            "广告位报告",
            "广告位",
            "placement report",
            "placements report",
            "placement",
            "top of search",
            "rest of search",
            "product pages",
        ],
    },
    {
        "id": "sp_advertised_product",
        "standard_name": "SP广告商品报告",
        "required": True,
        "patterns": [
            "广告商品报告",
            "广告商品",
            "advertised product",
            "advertised products",
            "advertised-product",
            "asin sku",
            "sku asin",
        ],
    },
    {
        "id": "campaign_ad_group_settings",
        "standard_name": "Campaign / Ad Group 设置表",
        "required": True,
        "patterns": [
            "campaign / ad group 设置",
            "campaign ad group 设置",
            "campaign设置",
            "ad group设置",
            "广告活动设置",
            "广告组设置",
            "campaign settings",
            "ad group settings",
            "campaign_ad_group_settings",
            "portfolio campaign ad group",
        ],
    },
    {
        "id": "sp_placement_daily",
        "standard_name": "SP广告位-每日明细",
        "required": False,
        "patterns": [
            "广告位-每日",
            "广告位每日",
            "placement daily",
            "placements daily",
            "daily placement",
        ],
    },
    {
        "id": "sp_keyword_daily",
        "standard_name": "SP关键词-每日明细",
        "required": False,
        "patterns": [
            "关键词-每日",
            "关键词每日",
            "keyword daily",
            "keywords daily",
            "daily keyword",
        ],
    },
    {
        "id": "hourly_budget_spend",
        "standard_name": "小时预算 / 小时花费报告",
        "required": False,
        "patterns": [
            "小时预算",
            "小时花费",
            "hourly budget",
            "hourly spend",
            "hourly cost",
            "budget hourly",
        ],
    },
    {
        "id": "business_target_profit",
        "standard_name": "商品业务数据 / 订单目标 / 利润信息",
        "required": False,
        "patterns": [
            "商品业务数据",
            "订单目标",
            "利润信息",
            "目标acos",
            "目标cpa",
            "business data",
            "profit",
            "order target",
            "target acos",
            "target cpa",
        ],
    },
    {
        "id": "cross_ad_product_assets",
        "standard_name": "SPV / SB / SBV 素材与账户条件表",
        "required": False,
        "patterns": [
            "素材与账户条件",
            "素材账户条件",
            "spv sb sbv",
            "video brand store assets",
            "cross ad product assets",
        ],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Amazon ad report attachments from mailbox and build an AGENTS import manifest."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to JSON config.")
    parser.add_argument(
        "--source-dir",
        help="Import files from a local folder instead of connecting to mailbox. Useful for manual first runs.",
    )
    parser.add_argument("--since", help="Override mailbox start date, YYYY-MM-DD.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and show planned run only.")
    parser.add_argument(
        "--allow-missing-env",
        action="store_true",
        help="Allow dry-run to pass even when mailbox env vars are missing.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def default_config() -> dict:
    return {
        "imap": {
            "host_env": "AMAZON_REPORT_IMAP_HOST",
            "port": 993,
            "username_env": "AMAZON_REPORT_MAIL_USER",
            "password_env": "AMAZON_REPORT_MAIL_APP_PASSWORD",
            "mailbox": "INBOX",
        },
        "search": {
            "lookback_days": 10,
            "from_contains": ["amazon", "advertising.amazon", "sellercentral.amazon"],
            "subject_contains": ["report", "reports", "广告", "报表", "sponsored", "campaign"],
            "unseen_only": False,
        },
        "output": {
            "save_root": str(DEFAULT_SAVE_ROOT),
            "write_latest_pointer": True,
        },
        "attachments": {
            "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
            "extract_zip": True,
        },
        "analysis": {
            "default_product_stage": "老品推广",
            "output_root": str(PROJECT_ROOT / "outputs" / "weekly_amazon_ads"),
        },
    }


def load_config(path: Path) -> dict:
    return deep_merge(default_config(), load_json(path))


def env_value(config: dict, section: str, key: str) -> str | None:
    env_name = config[section].get(key)
    if not env_name:
        return None
    return os.environ.get(env_name)


def missing_env(config: dict) -> list[str]:
    missing = []
    for key in ("host_env", "username_env", "password_env"):
        env_name = config["imap"].get(key)
        if env_name and not os.environ.get(env_name):
            missing.append(env_name)
    return missing


def safe_filename(name: str, fallback: str = "attachment") -> str:
    name = str(make_header(decode_header(name or fallback)))
    name = name.replace("/", "_").replace("\\", "_").strip()
    name = re.sub(r"[\x00-\x1f\x7f]", "_", name)
    name = re.sub(r"\s+", " ", name)
    return name[:180] or fallback


def safe_dirname(name: str) -> str:
    name = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", name, flags=re.UNICODE)
    return name.strip("._")[:120] or "report"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold())


def message_header(msg: email.message.Message, name: str) -> str:
    raw = msg.get(name, "")
    return str(make_header(decode_header(raw)))


def imap_since_date(config: dict, override_since: str | None) -> dt.date:
    if override_since:
        return dt.date.fromisoformat(override_since)
    days = int(config["search"].get("lookback_days", 10))
    return dt.date.today() - dt.timedelta(days=days)


def imap_date(value: dt.date) -> str:
    return value.strftime("%d-%b-%Y")


def message_matches(msg: email.message.Message, config: dict) -> bool:
    sender = normalize_text(message_header(msg, "From"))
    subject = normalize_text(message_header(msg, "Subject"))

    from_filters = [normalize_text(v) for v in config["search"].get("from_contains", []) if v]
    subject_filters = [normalize_text(v) for v in config["search"].get("subject_contains", []) if v]

    from_ok = True if not from_filters else any(v in sender for v in from_filters)
    subject_ok = True if not subject_filters else any(v in subject for v in subject_filters)
    return from_ok and subject_ok


def save_payload(
    payload: bytes,
    original_name: str,
    destination: Path,
    source_meta: dict,
) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    filename = safe_filename(original_name)
    base = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = destination / filename
    counter = 2
    while candidate.exists():
        candidate = destination / f"{base}_{counter}{suffix}"
        counter += 1
    candidate.write_bytes(payload)
    return {
        "path": str(candidate),
        "filename": candidate.name,
        "extension": candidate.suffix.casefold(),
        "sha256": sha256_file(candidate),
        "bytes": candidate.stat().st_size,
        "source": source_meta,
    }


def extract_zip(path: Path, destination: Path, source_meta: dict, allowed: set[str]) -> list[dict]:
    extracted = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            inner_name = safe_filename(Path(info.filename).name)
            if Path(inner_name).suffix.casefold() not in allowed - {".zip"}:
                continue
            payload = archive.read(info)
            meta = dict(source_meta)
            meta["zip_source"] = str(path)
            meta["zip_member"] = info.filename
            extracted.append(save_payload(payload, inner_name, destination, meta))
    return extracted


def download_from_mailbox(config: dict, run_dir: Path, since: dt.date) -> tuple[list[dict], list[dict]]:
    allowed = {ext.casefold() for ext in config["attachments"].get("allowed_extensions", [])}
    host = env_value(config, "imap", "host_env")
    username = env_value(config, "imap", "username_env")
    password = env_value(config, "imap", "password_env")
    port = int(config["imap"].get("port", 993))
    mailbox = config["imap"].get("mailbox", "INBOX")
    unseen_only = bool(config["search"].get("unseen_only", False))

    if not host or not username or not password:
        raise RuntimeError(f"Missing mailbox env vars: {', '.join(missing_env(config))}")

    raw_dir = run_dir / "raw"
    extracted_dir = run_dir / "extracted"
    downloaded = []
    inspected_messages = []
    search_terms = ["SINCE", imap_date(since)]
    if unseen_only:
        search_terms.append("UNSEEN")

    context = ssl.create_default_context()
    with imaplib.IMAP4_SSL(host, port, ssl_context=context) as client:
        client.login(username, password)
        status, select_data = client.select(mailbox)
        if status != "OK":
            detail = ""
            if select_data:
                detail = f": {select_data[0].decode('utf-8', errors='replace')}"
            raise RuntimeError(f"IMAP select failed for mailbox {mailbox}{detail}")
        status, data = client.search(None, *search_terms)
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")
        message_ids = data[0].split()
        for message_id in message_ids:
            status, msg_data = client.fetch(message_id, "(RFC822)")
            if status != "OK":
                continue
            raw_message = msg_data[0][1]
            msg = email.message_from_bytes(raw_message)
            sender = message_header(msg, "From")
            subject = message_header(msg, "Subject")
            date_header = message_header(msg, "Date")
            matched = message_matches(msg, config)
            message_meta = {
                "imap_message_id": message_id.decode("ascii", errors="replace"),
                "from": sender,
                "subject": subject,
                "date": date_header,
                "matched_filters": matched,
            }
            inspected_messages.append(message_meta)
            if not matched:
                continue
            for part in msg.walk():
                filename = part.get_filename()
                if not filename:
                    continue
                filename = str(make_header(decode_header(filename)))
                extension = Path(filename).suffix.casefold()
                if extension not in allowed:
                    continue
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                saved = save_payload(payload, filename, raw_dir, message_meta)
                downloaded.append(saved)
                if extension == ".zip" and config["attachments"].get("extract_zip", True):
                    downloaded.extend(extract_zip(Path(saved["path"]), extracted_dir, message_meta, allowed))
        client.close()
        client.logout()
    return downloaded, inspected_messages


def import_from_source_dir(config: dict, source_dir: Path, run_dir: Path) -> list[dict]:
    allowed = {ext.casefold() for ext in config["attachments"].get("allowed_extensions", [])}
    raw_dir = run_dir / "raw"
    extracted_dir = run_dir / "extracted"
    downloaded = []

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        extension = path.suffix.casefold()
        if extension not in allowed:
            continue
        payload = path.read_bytes()
        meta = {
            "source_dir": str(source_dir),
            "original_path": str(path),
            "matched_filters": True,
        }
        saved = save_payload(payload, path.name, raw_dir, meta)
        downloaded.append(saved)
        if extension == ".zip" and config["attachments"].get("extract_zip", True):
            downloaded.extend(extract_zip(Path(saved["path"]), extracted_dir, meta, allowed))
    return downloaded


def classify_file(path: Path) -> dict | None:
    filename_text = normalize_text(path.name)
    best = None
    for rule in REPORT_RULES:
        matched = [pattern for pattern in rule["patterns"] if normalize_text(pattern) in filename_text]
        if not matched:
            continue
        score = len(matched)
        if not best or score > best["score"]:
            best = {
                "id": rule["id"],
                "standard_name": rule["standard_name"],
                "required": rule["required"],
                "matched_patterns": matched,
                "score": score,
                "confidence": "medium" if score == 1 else "high",
            }
    return best


def classify_reports(downloaded: list[dict], run_dir: Path) -> tuple[dict, list[dict]]:
    classified: dict[str, list[dict]] = {rule["standard_name"]: [] for rule in REPORT_RULES}
    unclassified = []
    classified_root = run_dir / "classified"

    for item in downloaded:
        path = Path(item["path"])
        if path.suffix.casefold() == ".zip":
            continue
        match = classify_file(path)
        if not match:
            unclassified.append(item)
            continue

        report_dir = classified_root / safe_dirname(match["standard_name"])
        report_dir.mkdir(parents=True, exist_ok=True)
        destination = report_dir / path.name
        counter = 2
        while destination.exists():
            destination = report_dir / f"{path.stem}_{counter}{path.suffix}"
            counter += 1
        shutil.copy2(path, destination)
        classified_item = dict(item)
        classified_item.update(
            {
                "classified_path": str(destination),
                "standard_name": match["standard_name"],
                "report_id": match["id"],
                "confidence": match["confidence"],
                "matched_patterns": match["matched_patterns"],
            }
        )
        classified[match["standard_name"]].append(classified_item)

    return classified, unclassified


def build_manifest(
    config: dict,
    run_dir: Path,
    since: dt.date | None,
    downloaded: list[dict],
    inspected_messages: list[dict],
    classified: dict,
    unclassified: list[dict],
    source_mode: str,
) -> dict:
    required_names = [rule["standard_name"] for rule in REPORT_RULES if rule["required"]]
    recommended_names = [rule["standard_name"] for rule in REPORT_RULES if not rule["required"]]
    missing_required = [name for name in required_names if not classified.get(name)]
    missing_recommended = [name for name in recommended_names if not classified.get(name)]
    analysis_output_root = Path(config["analysis"]["output_root"])
    analysis_output_dir = analysis_output_root / run_dir.name

    return {
        "run_id": run_dir.name,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "source_mode": source_mode,
        "mail_since": since.isoformat() if since else None,
        "run_dir": str(run_dir),
        "analysis_output_dir": str(analysis_output_dir),
        "downloaded_count": len(downloaded),
        "inspected_message_count": len(inspected_messages),
        "downloaded_files": downloaded,
        "inspected_messages": inspected_messages,
        "classified_reports": classified,
        "unclassified_files": unclassified,
        "missing_required_reports": missing_required,
        "missing_recommended_reports": missing_recommended,
        "required_reports": required_names,
        "recommended_reports": recommended_names,
        "notes": [
            "老品推广诊断只能使用当前链接 / 当前 Campaign / 当前广告组真实报表。",
            "类目历史出单词和 ABA 词库只能作为选词参考或流量结构判断，不能替代当前老品报表。",
            "文件分类主要基于文件名；confidence 不是业务结论，低置信或未分类文件需人工确认。",
        ],
    }


def write_manifest(manifest: dict, run_dir: Path, config: dict) -> Path:
    path = run_dir / "manifest.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    if config["output"].get("write_latest_pointer", True):
        latest = Path(config["output"]["save_root"]) / "latest_run.txt"
        latest.write_text(str(run_dir) + "\n", encoding="utf-8")
    return path


def write_analysis_prompt(manifest: dict, run_dir: Path) -> Path:
    classified_lines = []
    for name, items in manifest["classified_reports"].items():
        if not items:
            continue
        files = "；".join(str(Path(item["classified_path"])) for item in items)
        classified_lines.append(f"- {name}: {files}")
    if not classified_lines:
        classified_lines.append("- 未识别到标准老品报表。")

    missing_required = manifest["missing_required_reports"] or ["无"]
    missing_recommended = manifest["missing_recommended_reports"] or ["无"]
    search_term_report_names = (
        "SP搜索词-按词-汇总",
        "SP搜索词-按词-每日明细",
    )
    has_search_term_history = any(manifest["classified_reports"].get(name) for name in search_term_report_names)
    if has_search_term_history:
        missing_action_rule = """必须报表缺失时，先确认已识别的搜索词表是否来自当前链接。如果是，允许进入“有限数据老广告优化模式”：输出词根历史订单、CVR、ACOS、历史词根优化分和词根层候选方案。每个缺失模块必须写 `【缺失数据】数据不足，无法准确判断`。

此模式不得写具体 Campaign / 广告组、Bid、广告位调整、否词实施、暂停、重建或跨广告产品放量。如果无法确认搜索词属于当前链接，退回为仅输出缺失影响。"""
    else:
        missing_action_rule = """如果必须报表缺失，不要编造后台动作；只能输出“缺少老品诊断源数据”以及缺失影响。可以把未分类文件列为待人工确认。"""

    body = f"""# 每周 Amazon 广告报表分析提示

项目目录：`{manifest["project_root"]}`
本次导入目录：`{manifest["run_dir"]}`
分析输出目录：`{manifest["analysis_output_dir"]}`

## 必须读取

1. `AGENTS.md`
2. `rules/domains/old-product/README.md`
3. `rules/domains/search-term/README.md`
4. `thresholds/README.md`
5. `rules/output/output-rules.md`
6. `contracts/data-input.md`

## 已识别报表

{chr(10).join(classified_lines)}

## 缺失报表

必须缺失：{", ".join(missing_required)}

建议缺失：{", ".join(missing_recommended)}

## 分析要求

按老品推广规则分析。必须先说明观察周期、已导入报表、缺失报表影响、数据充分度和对象映射是否可靠。

{missing_action_rule}

如果报表齐全，输出：

1. 产品策略摘要。
2. 老广告优化表。
3. 第一张核心表下方的 `判断依据与设计逻辑` 自然段，使用 `【当前报表】`、`【品类阈值/用户固定规则】`、`【人工输入/业务目标】`、`【缺失数据】` 等来源标签。
4. 新广告设置表。
5. 需要人工确认的报表、目标 ACOS/CPA、售价、毛利、库存、Coupon、Review 信息。

禁止把 `reference/category-history/` 或 ABA 词库当成当前老品诊断报表。
"""
    path = run_dir / "analysis_prompt.md"
    path.write_text(body, encoding="utf-8")
    return path


def print_summary(manifest: dict, manifest_path: Path, prompt_path: Path) -> None:
    print(f"Run: {manifest['run_id']}")
    print(f"Downloaded files: {manifest['downloaded_count']}")
    print(f"Manifest: {manifest_path}")
    print(f"Analysis prompt: {prompt_path}")
    if manifest["missing_required_reports"]:
        print("Missing required reports:")
        for name in manifest["missing_required_reports"]:
            print(f"  - {name}")
    else:
        print("Missing required reports: none")
    if manifest["unclassified_files"]:
        print("Unclassified files:")
        for item in manifest["unclassified_files"]:
            print(f"  - {item['path']}")


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    config = load_config(config_path)
    save_root = Path(config["output"]["save_root"]).expanduser().resolve()
    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = save_root / run_id
    since = imap_since_date(config, args.since) if not args.source_dir else None

    if args.dry_run:
        missing = [] if args.source_dir else missing_env(config)
        print(f"Config: {config_path}")
        print(f"Save root: {save_root}")
        print(f"Source mode: {'local folder' if args.source_dir else 'mailbox'}")
        if since:
            print(f"Mailbox since: {since.isoformat()}")
        if missing:
            print("Missing mailbox env vars:")
            for name in missing:
                print(f"  - {name}")
            return 0 if args.allow_missing_env else 2
        print("Dry run passed.")
        return 0

    run_dir.mkdir(parents=True, exist_ok=False)

    inspected_messages: list[dict] = []
    if args.source_dir:
        downloaded = import_from_source_dir(config, Path(args.source_dir).expanduser().resolve(), run_dir)
        source_mode = "local_source_dir"
    else:
        downloaded, inspected_messages = download_from_mailbox(config, run_dir, since)
        source_mode = "mailbox_imap"

    classified, unclassified = classify_reports(downloaded, run_dir)
    manifest = build_manifest(
        config=config,
        run_dir=run_dir,
        since=since,
        downloaded=downloaded,
        inspected_messages=inspected_messages,
        classified=classified,
        unclassified=unclassified,
        source_mode=source_mode,
    )
    manifest_path = write_manifest(manifest, run_dir, config)
    prompt_path = write_analysis_prompt(manifest, run_dir)
    print_summary(manifest, manifest_path, prompt_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
