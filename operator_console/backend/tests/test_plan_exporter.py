from __future__ import annotations

from pathlib import Path
import sys

from openpyxl import Workbook, load_workbook


BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from plan_exporter import export_new_product_architecture, export_sp_optimization_plan  # noqa: E402


def test_new_product_workbook_is_rendered_from_validated_codex_rows(tmp_path: Path) -> None:
    evidence = tmp_path / "新品候选证据包.xlsx"
    workbook = Workbook()
    workbook.active.title = "ABA选词表"
    workbook.active.append(["ASIN", "搜索词"])
    workbook.active.append(["B0ABC12345", "5x7 area rug"])
    workbook.create_sheet("新广告设置表").append(["旧Python候选"])
    workbook.save(evidence)
    result = {
        "executive_summary": "Codex最终架构",
        "new_product_architecture": [
            {
                "campaign_name": "待人工命名",
                "ad_group_name": "001-SP-尺寸-词组-area-5x7-test",
                "asin": "B0ABC12345",
                "structure_mode": "SINGLE_ASIN_CONTROL",
                "operation": "新增广告组",
                "match_type": "词组",
                "daily_budget": 20,
                "bid": "待人工配置",
                "bidding_strategy": "动态竞价-只降低",
                "placement": "待人工配置",
                "role": "Phrase承接",
                "target": "5x7 area rug",
                "negative_exact": "",
                "reason": "通过相关性与搜索量门",
            }
        ],
    }
    output = tmp_path / "广告架构设计方案.xlsx"
    export_new_product_architecture(
        result,
        {"artifacts": [str(evidence)], "analysis_asins": ["B0ABC12345"]},
        {"outcome": "PASS_CANDIDATE_ONLY"},
        output,
    )
    rendered = load_workbook(output, data_only=True)
    assert rendered.sheetnames == ["ABA选词表", "新广告设置表"]
    assert rendered["新广告设置表"]["F2"].value == "词组"
    assert rendered["新广告设置表"]["L2"].value == "5x7 area rug"
    assert rendered["新广告设置表"]["A2"].value != "旧Python候选"


def test_sp_plan_has_human_review_tables(tmp_path: Path) -> None:
    result = {
        "executive_summary": "仅供人工复核",
        "recommendations": [
            {
                "priority": "P1",
                "action": "[B0ABC12345] 建立独立主推控制单元",
                "reason": "需要独立预算",
                "evidence": "Campaign A 历史表现",
                "risk": "缺少Amazon ID",
            }
        ],
    }
    preprocessing = {
        "status": "READY_FOR_ANALYSIS",
        "analysis_asins": ["B0ABC12345"],
        "auto_period": {"start": "2026-07-01", "end": "2026-07-30"},
        "artifacts": [],
    }
    validation = {"outcome": "PASS_CANDIDATE_ONLY"}
    output = tmp_path / "SP广告优化方案.xlsx"

    export_sp_optimization_plan(result, preprocessing, validation, output)
    workbook = load_workbook(output, data_only=True)

    assert workbook.sheetnames == ["产品策略摘要", "老广告优化表", "新广告设置表"]
    assert workbook["产品策略摘要"]["A2"].value == "B0ABC12345"
    assert workbook["产品策略摘要"]["G2"].value == 1
    assert workbook["产品策略摘要"]["H2"].value == "B0ABC12345"
    assert workbook["老广告优化表"]["C2"].value == "待补Amazon ID"
    assert workbook["新广告设置表"]["E2"].value == "SINGLE_ASIN_CONTROL"
    assert workbook["新广告设置表"]["N2"].value == "APPROVAL_REQUIRED"
