from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_release_prep_documents_adapter_tiers_consistently() -> None:
    readme = _read("README.md")
    prep = _read("docs/v1_release_prep.md")
    readiness = _read("docs/v1_readiness_review.md")

    for text in (readme, prep, readiness):
        assert "Python" in text
        assert "TypeScript" in text
        assert "Go" in text
        assert "reference" in text
        assert "pilot" in text


def test_release_prep_documents_repository_root_policy_consistently() -> None:
    readme = _read("README.md")
    freeze = _read("docs/protocol_freeze.md")
    prep = _read("docs/v1_release_prep.md")

    for text in (readme, freeze, prep):
        assert "parse . --json" in text
        assert "map . --json" in text
        assert "validate . --json" in text
        assert "lint . --json" in text
        assert "parity fixtures" in text
