from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_release_notes_draft_matches_release_prep_messaging() -> None:
    release_notes = _read("docs/v1_release_notes_draft.md")
    release_prep = _read("docs/v1_release_prep.md")
    agent_contract = _read("docs/agent_contract.md")

    for text in (release_notes, release_prep, agent_contract):
        assert "Python" in text
        assert "TypeScript" in text
        assert "Go" in text

    assert "reference" in release_notes
    assert "pilot" in release_notes
    assert "semantic protocol" in release_notes
    assert "shell-driven" in agent_contract
