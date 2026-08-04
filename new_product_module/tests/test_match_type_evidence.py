from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.match_type_evidence import (  # noqa: E402
    enrich_keyword_evidence,
    load_match_type_evidence,
)


def test_missing_sources_remain_explicitly_pending(tmp_path: Path) -> None:
    relevance = tmp_path / "relevance"
    volume = tmp_path / "volume"
    relevance.mkdir()
    volume.mkdir()
    evidence = load_match_type_evidence(relevance, volume)
    rows = enrich_keyword_evidence(
        [{"search_term": "5x7 area rug", "normalized_root": "area rug"}],
        asin="B0ABC12345",
        marketplace="US",
        evidence=evidence,
    )
    assert rows[0]["match_type_evidence_status"] == (
        "RELEVANCE_PENDING+ROOT_SEARCH_VOLUME_PENDING"
    )
    assert {item["code"] for item in evidence.issues} == {
        "RELEVANCE_SOURCE_PENDING",
        "SEARCH_VOLUME_SOURCE_PENDING",
    }


def test_relevance_and_root_demand_are_joined_without_aba_rank_conversion(tmp_path: Path) -> None:
    relevance = tmp_path / "relevance.csv"
    relevance.write_text(
        "ASIN,搜索词,相关性结论,相关性得分,判断依据\n"
        "B0ABC12345,5x7 area rug,HIGH,95,尺寸和类型匹配\n",
        encoding="utf-8",
    )
    volume = tmp_path / "volume.csv"
    volume.write_text(
        "搜索词,规范词根,月份,月搜索量,站点\n"
        "5x7 area rug,area rug,2026-06,6000,US\n"
        "washable area rug,area rug,2026-06,3000,US\n"
        "vintage area rug,area rug,2026-06,1000,US\n"
        "5x7 area rug,area rug,2026-07,8000,US\n"
        "washable area rug,area rug,2026-07,2000,US\n"
        "vintage area rug,area rug,2026-07,2000,US\n",
        encoding="utf-8",
    )
    evidence = load_match_type_evidence(relevance, volume)
    row = enrich_keyword_evidence(
        [{"search_term": "5x7 area rug", "normalized_root": "area rug", "aba_rank": 999999}],
        asin="B0ABC12345",
        marketplace="US",
        evidence=evidence,
    )[0]
    assert row["match_type_evidence_status"] == "READY"
    assert row["relevance_level"] == "HIGH"
    assert row["monthly_search_volume"] == 7000
    assert row["root_monthly_search_volume"] == 11000
    assert row["root_distinct_query_count"] == 3
    assert row["root_top3_volume_share"] == 1
    assert row["aba_rank"] == 999999


def test_conflicting_duplicate_search_volume_is_blocked(tmp_path: Path) -> None:
    volume = tmp_path / "volume.csv"
    volume.write_text(
        "搜索词,规范词根,月份,月搜索量,站点\n"
        "area rug,area rug,2026-07,10000,US\n"
        "area rug,area rug,2026-07,12000,US\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="数据冲突"):
        load_match_type_evidence(None, volume)
