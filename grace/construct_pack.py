# @grace.module grace.construct_pack
# @grace.purpose Define declarative construct-pack metadata so agents can extend specific language shapes without inventing new parser semantics or editing core layers per construct.
# @grace.interfaces GraceConstructPack, apply_construct_packs
# @grace.invariant Construct packs may only extend or specialize language-pack metadata declaratively; they must not change core semantic contracts or patch behavior.

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from grace.treesitter_base import TreeSitterBlockQuerySpec, TreeSitterLanguageSpec

_Item = TypeVar("_Item")


# @grace.anchor grace.construct_pack.GraceConstructPack
# @grace.complexity 2
@dataclass(frozen=True, slots=True)
class GraceConstructPack:
    pack_name: str
    language_name: str
    additional_file_extensions: tuple[str, ...] = ()
    additional_line_comment_prefixes: tuple[str, ...] = ()
    additional_block_comment_delimiters: tuple[tuple[str, str], ...] = ()
    additional_block_query_specs: tuple[TreeSitterBlockQuerySpec, ...] = ()
    override_language_factory: Callable[[], object] | None = None
    bootstrap_safe: bool | None = None


def _merge_unique(items: tuple[_Item, ...], additions: tuple[_Item, ...]) -> tuple[_Item, ...]:
    merged: list[_Item] = list(items)
    for item in additions:
        if item not in merged:
            merged.append(item)
    return tuple(merged)


# @grace.anchor grace.construct_pack.apply_construct_packs
# @grace.complexity 4
# @grace.belief Construct packs should stay purely declarative: merge metadata deterministically on top of a base language spec so new constructs can be onboarded without bespoke parser code or core rewrites.
def apply_construct_packs(
    base_spec: TreeSitterLanguageSpec,
    packs: tuple[GraceConstructPack, ...],
) -> TreeSitterLanguageSpec:
    applicable_packs = tuple(
        pack for pack in packs if pack.language_name == base_spec.language_name
    )
    if not applicable_packs:
        return base_spec

    file_extensions = base_spec.file_extensions
    line_comment_prefixes = base_spec.line_comment_prefixes
    block_comment_delimiters = base_spec.block_comment_delimiters
    block_query_specs = base_spec.block_query_specs
    language_factory = base_spec.language_factory

    for pack in applicable_packs:
        file_extensions = _merge_unique(file_extensions, pack.additional_file_extensions)
        line_comment_prefixes = _merge_unique(
            line_comment_prefixes,
            pack.additional_line_comment_prefixes,
        )
        block_comment_delimiters = _merge_unique(
            block_comment_delimiters,
            pack.additional_block_comment_delimiters,
        )
        block_query_specs = _merge_unique(
            block_query_specs,
            pack.additional_block_query_specs,
        )
        if pack.override_language_factory is not None:
            language_factory = pack.override_language_factory

    return TreeSitterLanguageSpec(
        language_name=base_spec.language_name,
        file_extensions=file_extensions,
        language_factory=language_factory,
        line_comment_prefixes=line_comment_prefixes,
        block_query_specs=block_query_specs,
        block_comment_delimiters=block_comment_delimiters,
    )


__all__ = ["GraceConstructPack", "apply_construct_packs"]
