from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


BRAND = "3F8F34"
BRAND_DARK = "1F5F2A"
BRAND_SOFT = "E8F3E4"
INK = "1E293B"
MUTED = "64748B"
LINE = "DCE6DD"
WARNING = "FFF4DE"
ASIN_PATTERN = re.compile(r"\[?(B0[A-Z0-9]{8})\]?")


def export_new_product_architecture(
    result: dict[str, Any],
    preprocessing: dict[str, Any],
    validation: dict[str, Any],
    output_path: Path,
) -> Path:
    """Render the final two-sheet workbook only from validated Codex rows."""

    evidence_path = next(
        (
            Path(str(raw))
            for raw in preprocessing.get("artifacts", [])
            if Path(str(raw)).suffix.lower() in {".xlsx", ".xlsm"} and Path(str(raw)).is_file()
        ),
        None,
    )
    if evidence_path is not None:
        workbook = load_workbook(evidence_path)
    else:
        workbook = Workbook()
        workbook.active.title = "ABA选词表"
    for sheet_name in list(workbook.sheetnames):
        if sheet_name != "ABA选词表":
            del workbook[sheet_name]
    sheet = workbook.create_sheet("新广告设置表")
    headers = [
        "Campaign 名称",
        "广告组名称",
        "ASIN",
        "结构模式",
        "操作",
        "匹配方式",
        "预算",
        "Bid",
        "投放策略",
        "TOS/ROS/PP",
        "投放角色/主投",
        "投放词/词根/类目",
        "精准否定词",
        "判断依据",
        "需人工确认",
        "Validator",
    ]
    sheet.append(headers)
    rows = result.get("new_product_architecture") or []
    if not rows:
        sheet.append(
            [
                "不新建",
                "不新建",
                (preprocessing.get("analysis_asins") or ["待识别"])[0],
                "SINGLE_ASIN_CONTROL",
                "不新建",
                "待补数据",
                "不适用",
                "不适用",
                "不适用",
                "不适用",
                "观察",
                "",
                "",
                result.get("executive_summary") or "当前没有通过验证的广告架构",
                "是",
                validation.get("outcome") or "BLOCKED",
            ]
        )
    else:
        for row in rows:
            sheet.append(
                [
                    row.get("campaign_name"),
                    row.get("ad_group_name"),
                    row.get("asin"),
                    row.get("structure_mode"),
                    row.get("operation"),
                    row.get("match_type"),
                    row.get("daily_budget"),
                    row.get("bid"),
                    row.get("bidding_strategy"),
                    row.get("placement"),
                    row.get("role"),
                    row.get("target"),
                    row.get("negative_exact"),
                    row.get("reason"),
                    "是",
                    validation.get("outcome") or "待校验",
                ]
            )
    for target in workbook.worksheets:
        _style_sheet(target)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    return output_path


def export_sp_optimization_plan(
    result: dict[str, Any],
    preprocessing: dict[str, Any],
    validation: dict[str, Any],
    output_path: Path,
) -> Path:
    """Create the human-review workbook for the SP optimization page.

    The workbook never upgrades missing names or local ids into Amazon immutable
    ids.  Unknown execution fields stay visibly pending.
    """

    packets = _load_packets(preprocessing)
    workbook = Workbook()
    summary = workbook.active
    summary.title = "产品策略摘要"
    old_ads = workbook.create_sheet("老广告优化表")
    new_ads = workbook.create_sheet("新广告设置表")

    _write_summary(summary, result, preprocessing, validation, packets)
    _write_old_ads(old_ads, result, validation, packets)
    _write_new_ads(new_ads, result, validation, packets)
    for sheet in workbook.worksheets:
        _style_sheet(sheet)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    return output_path


def _load_packets(preprocessing: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packets: dict[str, dict[str, Any]] = {}
    for raw in preprocessing.get("artifacts", []):
        path = Path(str(raw))
        if path.name != "ad_analysis_packet.json" or not path.is_file():
            continue
        try:
            import json

            packet = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        asin = str(packet.get("primary_asin") or "").strip()
        if asin:
            packets[asin] = packet
    return packets


def _write_summary(
    sheet: Any,
    result: dict[str, Any],
    preprocessing: dict[str, Any],
    validation: dict[str, Any],
    packets: dict[str, dict[str, Any]],
) -> None:
    headers = [
        "ASIN",
        "数据周期",
        "数据质量",
        "执行状态",
        "结构模式",
        "主经营目标",
        "广告ASIN数量",
        "广告ASIN清单",
        "当前分析粒度",
        "交叉归因限制",
        "核心诊断",
        "Validator",
        "人工批准",
    ]
    sheet.append(headers)
    period = preprocessing.get("auto_period") or {}
    period_text = _period_text(period)
    asins = preprocessing.get("analysis_asins") or list(packets)
    if not asins:
        asins = ["待识别"]
    for asin in asins:
        packet = packets.get(str(asin), {})
        settings = packet.get("settings") or []
        product_asins = _packet_product_asins(packet)
        if not product_asins and ASIN_PATTERN.fullmatch(str(asin).upper()):
            product_asins = [str(asin).upper()]
        modes = sorted({_structure_mode(item, packet) for item in settings}) or [
            "SINGLE_ASIN_CONTROL" if len(product_asins) == 1 else "UNKNOWN_STRUCTURE"
        ]
        objectives = sorted({_primary_objective(item) for item in settings}) or ["待人工确认"]
        sheet.append(
            [
                asin,
                period_text,
                packet.get("analysis_status") or preprocessing.get("status") or "待确认",
                packet.get("execution_status") or "HUMAN_EXECUTION_ONLY",
                " / ".join(modes),
                " / ".join(objectives),
                len(product_asins) if product_asins else "待识别",
                " / ".join(product_asins) or "待识别",
                packet.get("profile") or preprocessing.get("mode") or "待确认",
                "无同一行的搜索词×广告ASIN证据时，仅允许分别做搜索词层和广告商品层判断",
                _summary_for_asin(result, str(asin)),
                validation.get("outcome") or "待校验",
                "必须",
            ]
        )

    logic_row = sheet.max_row + 2
    sheet.cell(logic_row, 1, "判断依据与设计逻辑")
    sheet.cell(logic_row, 1).font = Font(bold=True, color=BRAND_DARK)
    sheet.merge_cells(start_row=logic_row + 1, start_column=1, end_row=logic_row + 1, end_column=len(headers))
    sheet.cell(
        logic_row + 1,
        1,
        "【当前报表】按广告商品、Campaign、Target、搜索词、广告位和设置表分别读取，"
        "不按名称把不同粒度硬拼成搜索词×广告ASIN归因。"
        "【用户固定规则】单ASIN控制单元与多ASIN发现池均可成立；主推、独立预算、精准收割或需清晰归因时拆出控制单元。"
        "【缺失数据】Amazon不可变ID、最新设置、经营目标、库存或利润缺失时，表内动作保持候选，目标值和回滚值不得补造。",
    )
    sheet.cell(logic_row + 1, 1).alignment = Alignment(wrap_text=True, vertical="top")
    sheet.row_dimensions[logic_row + 1].height = 72


def _write_old_ads(
    sheet: Any,
    result: dict[str, Any],
    validation: dict[str, Any],
    packets: dict[str, dict[str, Any]],
) -> None:
    headers = [
        "优先级",
        "ASIN",
        "Campaign ID",
        "本地临时ID",
        "Campaign 名称",
        "Ad Group ID",
        "广告组名称",
        "结构模式",
        "主经营目标",
        "分析粒度",
        "当前预算",
        "当前Bid",
        "投放策略",
        "当前状态",
        "结构/优化动作",
        "判断依据",
        "证据",
        "风险",
        "approval_status",
        "validator_outcome",
    ]
    sheet.append(headers)
    recommendations = result.get("recommendations") or []
    if not recommendations:
        sheet.append(["OBSERVE", "待识别", "待补Amazon ID", "", "", "待补Amazon ID", "", "UNKNOWN_STRUCTURE", "待人工确认", "数据不足", "", "", "", "", "无可用优化动作", result.get("executive_summary", ""), "", "", "APPROVAL_REQUIRED", validation.get("outcome", "待校验")])
        return

    for item in recommendations:
        asin = _extract_asin(item) or "待识别"
        packet = packets.get(asin, {})
        setting = _matching_setting(item, packet.get("settings") or [])
        sheet.append(
            [
                item.get("priority") or "OBSERVE",
                asin,
                "待补Amazon ID",
                setting.get("local_campaign_id") or "",
                setting.get("campaign") or "待定位",
                "待补Amazon ID",
                setting.get("ad_group") or "待定位",
                _structure_mode(setting, packet),
                _primary_objective(setting),
                packet.get("profile") or "待确认",
                setting.get("daily_budget"),
                setting.get("default_bid"),
                setting.get("targeting_type") or setting.get("bidding_strategy") or "待确认",
                setting.get("status") or "待确认",
                item.get("action") or "",
                item.get("reason") or "",
                item.get("evidence") or "",
                item.get("risk") or "",
                "APPROVAL_REQUIRED",
                validation.get("outcome") or "待校验",
            ]
        )


def _write_new_ads(
    sheet: Any,
    result: dict[str, Any],
    validation: dict[str, Any],
    packets: dict[str, dict[str, Any]],
) -> None:
    headers = [
        "Campaign 名称",
        "广告组名称",
        "ASIN",
        "类型",
        "结构模式",
        "主经营目标",
        "预算",
        "Bid",
        "投放策略",
        "TOS/ROS/PP",
        "投放词/词根/对象",
        "归因限制",
        "判断依据",
        "approval_status",
        "validator_outcome",
    ]
    sheet.append(headers)
    candidates = [item for item in result.get("recommendations") or [] if _is_new_structure_candidate(item)]
    if not candidates:
        sheet.append(["不新建", "不新建", "待识别", "不新建", "UNKNOWN_STRUCTURE", "待人工确认", "", "", "", "", "", "当前证据未形成新结构候选", result.get("executive_summary", ""), "APPROVAL_REQUIRED", validation.get("outcome", "待校验")])
        return
    for item in candidates:
        asin = _extract_asin(item) or "待识别"
        packet = packets.get(asin, {})
        setting = _matching_setting(item, packet.get("settings") or [])
        sheet.append(
            [
                "待人工命名",
                "待人工命名",
                asin,
                _candidate_type(item),
                "SINGLE_ASIN_CONTROL" if asin != "待识别" else "UNKNOWN_STRUCTURE",
                "主推/恢复目标待人工确认",
                "待人工配置",
                "待人工配置",
                setting.get("targeting_type") or "待人工配置",
                "待人工配置",
                "待从当前搜索词与Target证据映射",
                "建立唯一Campaign—Ad Group—Target—ASIN映射后才能形成后台动作",
                f"{item.get('reason', '')}；证据：{item.get('evidence', '')}",
                "APPROVAL_REQUIRED",
                validation.get("outcome") or "待校验",
            ]
        )


def _style_sheet(sheet: Any) -> None:
    sheet.freeze_panes = "A2"
    sheet.sheet_view.showGridLines = False
    thin = Side(style="thin", color=LINE)
    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor=BRAND_DARK)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(bottom=thin)
    sheet.row_dimensions[1].height = 34
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(color=INK, size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=thin)
        if row and str(row[0].value or "") in {"P0", "P1", "P2", "OBSERVE"}:
            row[0].fill = PatternFill("solid", fgColor=BRAND_SOFT if row[0].value != "P0" else WARNING)
            row[0].font = Font(bold=True, color=BRAND_DARK)
    widths = {
        1: 16,
        2: 16,
        3: 20,
        4: 22,
        5: 34,
        6: 20,
        7: 28,
        8: 24,
        9: 22,
        10: 24,
        11: 16,
        12: 16,
        13: 22,
        14: 18,
        15: 38,
        16: 46,
        17: 46,
        18: 38,
        19: 22,
        20: 22,
    }
    for index in range(1, sheet.max_column + 1):
        sheet.column_dimensions[get_column_letter(index)].width = widths.get(index, 20)
    sheet.auto_filter.ref = f"A1:{get_column_letter(sheet.max_column)}{max(1, sheet.max_row)}"


def _extract_asin(item: dict[str, Any]) -> str | None:
    text = " ".join(str(item.get(key) or "") for key in ("action", "reason", "evidence"))
    match = ASIN_PATTERN.search(text.upper())
    return match.group(1) if match else None


def _matching_setting(item: dict[str, Any], settings: list[dict[str, Any]]) -> dict[str, Any]:
    text = " ".join(str(item.get(key) or "") for key in ("action", "reason", "evidence"))
    for setting in settings:
        campaign = str(setting.get("campaign") or "")
        if campaign and campaign in text:
            return setting
    return settings[0] if len(settings) == 1 else {}


def _structure_mode(setting: dict[str, Any], packet: dict[str, Any] | None = None) -> str:
    text = " ".join(str(setting.get(key) or "") for key in ("campaign", "ad_group")).lower()
    if "清仓" in text or "捡漏" in text or "clearance" in text:
        return "CLEARANCE_OR_PICKUP"
    if any(token in text for token in ("全sku", "多库存", "多asin", "multi asin")):
        return "MIXED_INTENT_LEGACY"
    product_asins = _packet_product_asins(packet or {})
    if len(product_asins) == 1:
        return "SINGLE_ASIN_CONTROL"
    if len(product_asins) > 1:
        return "MULTI_ASIN_DISCOVERY_POOL_CANDIDATE"
    return "UNKNOWN_STRUCTURE"


def _primary_objective(setting: dict[str, Any]) -> str:
    mode = _structure_mode(setting)
    if mode == "CLEARANCE_OR_PICKUP":
        return "清仓/捡漏"
    if mode == "MIXED_INTENT_LEGACY":
        return "历史组合目标待确认"
    return "待人工确认"


def _summary_for_asin(result: dict[str, Any], asin: str) -> str:
    relevant = [str(item.get("action") or "") for item in result.get("recommendations") or [] if _extract_asin(item) == asin]
    return "；".join(relevant[:4]) or str(result.get("executive_summary") or "")


def _is_new_structure_candidate(item: dict[str, Any]) -> bool:
    text = " ".join(str(item.get(key) or "") for key in ("action", "reason"))
    return any(token in text for token in ("新建", "重建", "拆分", "承接", "主推", "独立"))


def _candidate_type(item: dict[str, Any]) -> str:
    text = str(item.get("action") or "")
    for token in ("拆分", "重建", "新建", "并入"):
        if token in text:
            return f"{token}候选"
    return "新增控制单元候选"


def _period_text(period: dict[str, Any]) -> str:
    start = period.get("start")
    end = period.get("end")
    return f"{start} 至 {end}" if start and end else "由报表自动识别"


def _packet_product_asins(packet: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for section in ("historical_metrics", "current_metrics"):
        metrics = packet.get(section) or {}
        for item in metrics.get("product") or []:
            match = ASIN_PATTERN.search(str(item.get("object_label") or "").upper())
            if match and match.group(1) not in values:
                values.append(match.group(1))
    primary = str(packet.get("primary_asin") or "").upper()
    if ASIN_PATTERN.fullmatch(primary) and primary not in values:
        values.append(primary)
    return sorted(values)
