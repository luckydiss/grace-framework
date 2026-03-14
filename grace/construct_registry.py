# @grace.module grace.construct_registry
# @grace.purpose Register declarative construct packs so agents can extend language coverage through external metadata rather than in-code query builders.
# @grace.interfaces register_construct_pack, get_construct_pack, get_construct_packs
# @grace.invariant Built-in construct packs are loaded from external TOML specs exactly once and remain deterministic by language name and pack name.

from __future__ import annotations

from typing import Dict

from grace.construct_pack import GraceConstructPack

_REGISTERED_CONSTRUCT_PACKS: Dict[str, Dict[str, GraceConstructPack]] = {}
_DEFAULT_CONSTRUCT_PACKS_REGISTERED = False


# @grace.anchor grace.construct_registry.register_construct_pack
# @grace.complexity 2
def register_construct_pack(pack: GraceConstructPack) -> None:
    language_packs = _REGISTERED_CONSTRUCT_PACKS.setdefault(pack.language_name, {})
    language_packs[pack.pack_name] = pack


# @grace.anchor grace.construct_registry.get_construct_pack
# @grace.complexity 2
def get_construct_pack(language_name: str, pack_name: str) -> GraceConstructPack | None:
    _ensure_default_construct_packs()
    return _REGISTERED_CONSTRUCT_PACKS.get(language_name, {}).get(pack_name)


# @grace.anchor grace.construct_registry.get_construct_packs
# @grace.complexity 2
def get_construct_packs(language_name: str) -> tuple[GraceConstructPack, ...]:
    _ensure_default_construct_packs()
    packs = _REGISTERED_CONSTRUCT_PACKS.get(language_name, {})
    return tuple(packs[name] for name in sorted(packs))


# @grace.anchor grace.construct_registry._ensure_default_construct_packs
# @grace.complexity 2
def _ensure_default_construct_packs() -> None:
    global _DEFAULT_CONSTRUCT_PACKS_REGISTERED
    if _DEFAULT_CONSTRUCT_PACKS_REGISTERED:
        return

    from grace.spec_loader import load_builtin_construct_packs, load_registered_builtin_language_packs

    for language_pack in load_registered_builtin_language_packs():
        for construct_pack in load_builtin_construct_packs(language_pack.language_name):
            register_construct_pack(construct_pack)
    _DEFAULT_CONSTRUCT_PACKS_REGISTERED = True


__all__ = [
    "GraceConstructPack",
    "get_construct_pack",
    "get_construct_packs",
    "register_construct_pack",
]
