from __future__ import annotations

from pathlib import Path

from grace.language_pack import GraceLanguagePackStatus
from grace.spec_registry import (
    get_language_pack,
    get_language_pack_for_path,
    get_registered_language_packs,
)


def test_registry_exposes_current_builtin_language_packs() -> None:
    packs = get_registered_language_packs()
    assert [pack.language_name for pack in packs] == ["go", "python", "typescript"]
    assert get_language_pack("python").status is GraceLanguagePackStatus.REFERENCE
    assert get_language_pack("typescript").status is GraceLanguagePackStatus.PILOT
    assert get_language_pack("go").status is GraceLanguagePackStatus.PILOT


def test_registry_routes_supported_paths_to_packs() -> None:
    assert get_language_pack_for_path(Path("demo.py")).language_name == "python"
    assert get_language_pack_for_path(Path("demo.ts")).language_name == "typescript"
    assert get_language_pack_for_path(Path("demo.go")).language_name == "go"


def test_registry_returns_none_for_unknown_suffix() -> None:
    assert get_language_pack_for_path(Path("README.md")) is None
