# @grace.module grace.language_pack
# @grace.purpose Define declarative language pack metadata so adapter selection can be driven by registered specs instead of hard-coded per-language dispatch branches.
# @grace.interfaces GraceLanguagePack, GraceLanguagePackStatus, build_treesitter_pack
# @grace.invariant Language packs remain declarative metadata only; they do not parse files themselves and do not change GraceFileModel or core semantic contracts.

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from grace.treesitter_base import TreeSitterLanguageSpec


# @grace.anchor grace.language_pack.GraceLanguagePackStatus
# @grace.complexity 1
class GraceLanguagePackStatus(str, Enum):
    REFERENCE = "reference"
    PILOT = "pilot"
    FALLBACK = "fallback"
    EXPERIMENTAL = "experimental"


# @grace.anchor grace.language_pack.GraceLanguagePack
# @grace.complexity 2
# @grace.belief Language packs should expose which construct packs are active so agents can inspect extension surfaces without reading registry internals.
@dataclass(frozen=True, slots=True)
class GraceLanguagePack:
    language_name: str
    file_extensions: tuple[str, ...]
    status: GraceLanguagePackStatus
    adapter_family: str
    adapter_factory: Callable[[], object]
    base_adapter_factory: Callable[[], object]
    bootstrap_safe: bool = True
    construct_pack_names: tuple[str, ...] = ()

    @property
    def primary_extension(self) -> str:
        return self.file_extensions[0] if self.file_extensions else ""


# @grace.anchor grace.language_pack.build_treesitter_pack
# @grace.complexity 3
# @grace.belief Tree-sitter pack construction should stay the single place where merged construct-pack metadata becomes runtime dispatch metadata, so registry callers can remain declarative.
def build_treesitter_pack(
    *,
    language_name: str,
    file_extensions: tuple[str, ...],
    status: GraceLanguagePackStatus,
    spec_factory: Callable[[], TreeSitterLanguageSpec],
    adapter_factory: Callable[[], object] | None = None,
    bootstrap_safe: bool = True,
    construct_pack_names: tuple[str, ...] = (),
) -> GraceLanguagePack:
    from grace.treesitter_base import TreeSitterAdapterBase

    def base_adapter_factory() -> object:
        return TreeSitterAdapterBase(spec_factory())

    return GraceLanguagePack(
        language_name=language_name,
        file_extensions=file_extensions,
        status=status,
        adapter_family="treesitter",
        adapter_factory=adapter_factory or base_adapter_factory,
        base_adapter_factory=base_adapter_factory,
        bootstrap_safe=bootstrap_safe,
        construct_pack_names=construct_pack_names,
    )


__all__ = [
    "GraceLanguagePack",
    "GraceLanguagePackStatus",
    "build_treesitter_pack",
]
