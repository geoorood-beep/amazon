from __future__ import annotations

from pathlib import Path
import sys


BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from server import artifact_content_disposition  # noqa: E402


def test_chinese_artifact_name_uses_rfc5987_and_ascii_fallback() -> None:
    value = artifact_content_disposition("SP广告优化方案.xlsx")

    value.encode("latin-1", "strict")
    assert 'filename="artifact.xlsx"' in value
    assert "filename*=UTF-8''SP%E5%B9%BF%E5%91%8A" in value
