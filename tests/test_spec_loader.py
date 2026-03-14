from pathlib import Path

from grace.spec_loader import (
    load_builtin_construct_packs,
    load_builtin_language_pack,
    load_language_pack_for_path,
    load_registered_builtin_language_packs,
)


def test_builtin_language_specs_load() -> None:
    packs = load_registered_builtin_language_packs()
    assert {pack.language_name for pack in packs} >= {"python", "typescript", "go"}


def test_builtin_pack_for_typescript_includes_construct_extensions() -> None:
    pack = load_language_pack_for_path(Path("component.tsx"))
    assert pack is not None
    assert pack.language_name == "typescript"
    assert ".tsx" in pack.file_extensions


def test_builtin_construct_pack_loads() -> None:
    packs = load_builtin_construct_packs("typescript")
    assert any(pack.pack_name == "typescript.tsx_function_components" for pack in packs)


def test_builtin_pack_load_by_name() -> None:
    pack = load_builtin_language_pack("python")
    assert pack.language_name == "python"
    assert pack.primary_extension == ".py"
