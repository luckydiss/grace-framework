from pathlib import Path

from grace.construct_pack import apply_construct_packs
from grace.construct_registry import get_construct_pack, get_construct_packs
from grace.spec_registry import _build_typescript_pack, get_language_pack, get_language_pack_for_path


def test_construct_registry_exposes_builtin_typescript_tsx_pack() -> None:
    pack = get_construct_pack("typescript", "typescript.tsx_function_components")

    assert pack is not None
    assert pack.additional_file_extensions == (".tsx",)


def test_construct_registry_returns_deterministic_order() -> None:
    packs = get_construct_packs("typescript")

    assert tuple(pack.pack_name for pack in packs) == ("typescript.tsx_function_components",)


def test_apply_construct_packs_extends_typescript_spec_for_tsx() -> None:
    typescript_pack = _build_typescript_pack()
    base_spec = typescript_pack.base_adapter_factory().spec
    merged = apply_construct_packs(base_spec, get_construct_packs("typescript"))

    assert ".ts" in merged.file_extensions
    assert ".tsx" in merged.file_extensions


def test_language_pack_routes_tsx_path_to_typescript() -> None:
    pack = get_language_pack("typescript")
    routed = get_language_pack_for_path(Path("App.tsx"))

    assert ".tsx" in pack.file_extensions
    assert routed is not None
    assert routed.language_name == "typescript"
