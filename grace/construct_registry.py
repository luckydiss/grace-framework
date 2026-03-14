# @grace.module grace.construct_registry
# @grace.purpose Register declarative construct packs so agents can extend language coverage through metadata instead of one-off adapter code.
# @grace.interfaces register_construct_pack, get_construct_pack, get_construct_packs
# @grace.invariant Construct-pack registration must remain deterministic and language-scoped; default packs should bootstrap once and return stable ordering by pack name.

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


def _build_typescript_tsx_function_components_pack() -> GraceConstructPack:
    from tree_sitter_typescript import language_tsx

    from grace.models import BlockKind
    from grace.treesitter_base import TreeSitterBlockQuerySpec

    return GraceConstructPack(
        pack_name="typescript.tsx_function_components",
        language_name="typescript",
        additional_file_extensions=(".tsx",),
        override_language_factory=language_tsx,
        additional_block_query_specs=(
            TreeSitterBlockQuerySpec(
                query="(program (export_statement declaration: (function_declaration name: (identifier) @name) @block))",
                kind=BlockKind.FUNCTION,
                symbol_capture="name",
                promote_async_kind=BlockKind.ASYNC_FUNCTION,
            ),
            TreeSitterBlockQuerySpec(
                query="(program (export_statement declaration: (lexical_declaration (variable_declarator name: (identifier) @name value: (arrow_function) @block))))",
                kind=BlockKind.FUNCTION,
                symbol_capture="name",
                promote_async_kind=BlockKind.ASYNC_FUNCTION,
                line_start_capture="block",
            ),
            TreeSitterBlockQuerySpec(
                query="(program (export_statement declaration: (class_declaration name: (type_identifier) @name) @block))",
                kind=BlockKind.CLASS,
                symbol_capture="name",
            ),
            TreeSitterBlockQuerySpec(
                query="(program (export_statement declaration: (lexical_declaration (variable_declarator name: (identifier) @owner value: (object (method_definition name: (property_identifier) @name) @block)))))",
                kind=BlockKind.METHOD,
                symbol_capture="name",
                owner_capture="owner",
                qualified_name_template="{owner_name}.{symbol_name}",
            ),
        ),
    )


# @grace.anchor grace.construct_registry._ensure_default_construct_packs
# @grace.complexity 2
def _ensure_default_construct_packs() -> None:
    global _DEFAULT_CONSTRUCT_PACKS_REGISTERED
    if _DEFAULT_CONSTRUCT_PACKS_REGISTERED:
        return

    register_construct_pack(_build_typescript_tsx_function_components_pack())
    _DEFAULT_CONSTRUCT_PACKS_REGISTERED = True


__all__ = [
    "GraceConstructPack",
    "get_construct_pack",
    "get_construct_packs",
    "register_construct_pack",
]
