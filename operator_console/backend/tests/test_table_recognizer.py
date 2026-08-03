from __future__ import annotations

from pathlib import Path
import sys

from openpyxl import Workbook
import pytest
import yaml


BACKEND = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from table_recognizer import load_catalog, recognize_new_product, scan_report_file, summarize_upload
from server import aggregation_only_result, has_complete_overlap_windows, requested_asins, safe_upload_name


CATALOG_PATH = ROOT / "config/operator_catalog.json"
RULES_PATH = ROOT / "new_product_module/config/category_rules.example.yaml"


def save_workbook(path: Path, rows: list[list[object]], sheet_name: str = "Sheet1") -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def test_new_product_import_normalizes_catalog_values(tmp_path: Path) -> None:
    source = tmp_path / "新品资料.xlsx"
    save_workbook(
        source,
        [
            ["说明", "此行不是表头"],
            ["ASIN", "SKU", "尺寸", "地毯类型", "风格", "颜色", "材质", "场景标签", "日订单目标"],
            ["B0ABC12345", "RUG-01", "5 × 7 ft", "区域地毯", "波西米亚", "Grey", "聚酯纤维", "客厅，卧室", 3],
        ],
        "产品信息",
    )

    result = recognize_new_product(source, load_catalog(CATALOG_PATH))

    assert result["sheet"] == "产品信息"
    assert result["fields"]["asin"] == "B0ABC12345"
    assert result["fields"]["size_spec"] == "5x7"
    assert result["fields"]["rug_type"] == "area_rug"
    assert result["fields"]["style"] == "boho"
    assert result["fields"]["color"] == "gray"
    assert result["fields"]["material"] == "polyester"
    assert result["fields"]["scene_tags"] == "living room,bedroom"
    assert result["fields"]["order_target_daily"] == "3"


def test_report_scan_detects_multiple_asins_and_date_range(tmp_path: Path) -> None:
    source = tmp_path / "SP广告商品报告.xlsx"
    save_workbook(
        source,
        [
            ["广告ASIN", "日期", "花费"],
            ["B0ABC12345", "2026-07-01", 10],
            ["B0XYZ98765", "2026/07/31", 20],
        ],
    )

    result = scan_report_file(source)

    assert result["asins"] == ["B0ABC12345", "B0XYZ98765"]
    assert result["period_start"] == "2026-07-01"
    assert result["period_end"] == "2026-07-31"


def test_upload_summary_combines_reports_and_product_recognition(tmp_path: Path) -> None:
    upload_root = tmp_path / "upload-12345678"
    product_dir = upload_root / "new_product"
    report_dir = upload_root / "reports"
    product_dir.mkdir(parents=True)
    report_dir.mkdir()

    save_workbook(product_dir / "产品.xlsx", [["ASIN", "尺寸", "类型"], ["B0ABC12345", "5x7", "area rug"]])
    save_workbook(report_dir / "报表.xlsx", [["Advertised ASIN", "Start Date", "End Date"], ["B0ABC12345", "2026-07-01", "2026-07-30"]])

    result = summarize_upload(upload_root, load_catalog(CATALOG_PATH))

    assert result["detected_asins"] == ["B0ABC12345"]
    assert result["period_start"] == "2026-07-01"
    assert result["period_end"] == "2026-07-30"
    assert result["recognized_product"]["fields"]["rug_type"] == "area_rug"
    assert result["paths"]["reports"] == str(report_dir)
    assert "old_product_workbook" not in result["paths"]


def test_operator_catalog_matches_new_product_rule_catalog() -> None:
    catalog = load_catalog(CATALOG_PATH)
    rules = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    values = {
        field: {item["value"] for item in options}
        for field, options in catalog["fields"].items()
    }
    mapping = rules["rug_size_type_mapping"]
    expected_sizes = set(mapping["runner_sizes"]) | set(mapping["doormat_sizes"]) | set(mapping["area_sizes"])
    scoring = rules["attribute_scoring"]

    assert values["size_spec"] == expected_sizes
    assert values["rug_type"] == set(rules["rug_type_baselines"])
    assert values["style"] == set(scoring["style"]["known_terms"])
    assert values["color"] == {"gray" if value == "grey" else value for value in scoring["color"]["known_terms"]}
    assert values["material"] == set(scoring["material"]["value_aliases"])
    assert values["scene_tags"] == set(scoring["region"]["known_terms"])


def test_upload_filename_rejects_path_traversal() -> None:
    assert safe_upload_name("SP广告商品报告.xlsx") == "SP广告商品报告.xlsx"
    with pytest.raises(ValueError):
        safe_upload_name("../outside.xlsx")
    with pytest.raises(ValueError):
        safe_upload_name(r"..\outside.xlsx")
    with pytest.raises(ValueError):
        safe_upload_name("payload.exe")


def test_requested_asins_supports_multiple_values_and_deduplicates() -> None:
    fields = {"asin": "B0ABC12345, b0xyz98765", "asins": "B0ABC12345"}
    assert requested_asins(fields) == ["B0ABC12345", "B0XYZ98765"]
    assert requested_asins({"asin": "not-an-asin"}) == []


def test_overlap_detector_requires_all_report_windows(tmp_path: Path) -> None:
    families = ("SP搜索词-按词", "SP投放对象报告", "SP广告位报告", "SP广告商品报告")
    for family in families:
        for grain in ("每日明细", "汇总"):
            for days in (7, 14, 30):
                (tmp_path / f"{family}-{grain}-近{days}天.xlsx").touch()
    assert has_complete_overlap_windows(tmp_path) is True
    (tmp_path / "SP广告商品报告-汇总-近7天.xlsx").unlink()
    assert has_complete_overlap_windows(tmp_path) is False


def test_aggregation_only_result_does_not_generate_advice() -> None:
    request = {"job_id": "JOB-1", "intent": "OLD_PRODUCT_OPTIMIZATION"}
    preprocessing = {
        "status": "READY_FOR_ANALYSIS",
        "analysis_asins": ["B0ABC12345"],
        "auto_period": {"start": "2026-07-01", "end": "2026-07-30"},
        "artifacts": ["/tmp/ad_analysis_packet.xlsx"],
    }
    result = aggregation_only_result(request, preprocessing)
    assert result["status"] == "READY_FOR_HUMAN_REVIEW"
    assert result["recommendations"] == []
    assert "尚未调用Codex" in result["executive_summary"]
    assert result["safety"]["execution_allowed"] is False
