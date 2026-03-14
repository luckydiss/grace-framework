# @grace.module grace.spec_registry
# @grace.purpose Register and expose declarative language packs so adapter dispatch can scale by external metadata instead of hard-coded Python pack builders.
# @grace.interfaces get_language_pack, get_language_pack_for_path, get_registered_language_packs, register_language_pack
# @grace.invariant Built-in language packs are loaded from external TOML specs exactly once; path-specific lookups may overlay repo-local specs without mutating the built-in registry.

from __future__ import annotations

from pathlib import Path

from grace.language_pack import GraceLanguagePack

_PACKS_BY_LANGUAGE: dict[str, GraceLanguagePack] = {}
_PACKS_BY_EXTENSION: dict[str, GraceLanguagePack] = {}
_DEFAULT_PACKS_REGISTERED = False


# @grace.anchor grace.spec_registry.register_language_pack
# @grace.complexity 2
def register_language_pack(pack: GraceLanguagePack) -> None:
    _PACKS_BY_LANGUAGE[pack.language_name] = pack
    for extension in pack.file_extensions:
        _PACKS_BY_EXTENSION[extension.lower()] = pack


# @grace.anchor grace.spec_registry.get_registered_language_packs
# @grace.complexity 2
def get_registered_language_packs() -> tuple[GraceLanguagePack, ...]:
    _ensure_default_packs()
    return tuple(sorted(_PACKS_BY_LANGUAGE.values(), key=lambda pack: pack.language_name))


# @grace.anchor grace.spec_registry.get_language_pack
# @grace.complexity 2
def get_language_pack(language_name: str) -> GraceLanguagePack:
    _ensure_default_packs()
    try:
        return _PACKS_BY_LANGUAGE[language_name]
    except KeyError as exc:
        raise LookupError(f"unknown GRACE language pack {language_name!r}") from exc


# @grace.anchor grace.spec_registry.get_language_pack_for_path
# @grace.complexity 3
def get_language_pack_for_path(path: str | Path) -> GraceLanguagePack | None:
    from grace.spec_loader import load_language_pack_for_path

    _ensure_default_packs()
    resolved = load_language_pack_for_path(path)
    if resolved is not None:
        return resolved
    suffix = Path(path).suffix.lower()
    return _PACKS_BY_EXTENSION.get(suffix)


# @grace.anchor grace.spec_registry._ensure_default_packs
# @grace.complexity 3
def _ensure_default_packs() -> None:
    global _DEFAULT_PACKS_REGISTERED
    if _DEFAULT_PACKS_REGISTERED:
        return

    from grace.spec_loader import load_registered_builtin_language_packs

    for pack in load_registered_builtin_language_packs():
        register_language_pack(pack)
    _DEFAULT_PACKS_REGISTERED = True


__all__ = [
    "get_language_pack",
    "get_language_pack_for_path",
    "get_registered_language_packs",
    "register_language_pack",
]
