# @grace.module grace.spec_registry
# @grace.purpose Register and expose declarative language packs so adapter dispatch can scale by metadata instead of bespoke hard-coded branches.
# @grace.interfaces get_language_pack, get_language_pack_for_path, get_registered_language_packs, register_language_pack
# @grace.invariant The registry is deterministic by extension and language name; built-in packs are loaded lazily and preserve fallback behavior for unknown suffixes.

from __future__ import annotations

from pathlib import Path

from grace.language_pack import GraceLanguagePack, GraceLanguagePackStatus, build_treesitter_pack

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
# @grace.complexity 2
def get_language_pack_for_path(path: str | Path) -> GraceLanguagePack | None:
    _ensure_default_packs()
    suffix = Path(path).suffix.lower()
    return _PACKS_BY_EXTENSION.get(suffix)


# @grace.anchor grace.spec_registry._ensure_default_packs
# @grace.complexity 3
def _ensure_default_packs() -> None:
    global _DEFAULT_PACKS_REGISTERED
    if _DEFAULT_PACKS_REGISTERED:
        return

    register_language_pack(_build_python_pack())
    register_language_pack(_build_typescript_pack())
    register_language_pack(_build_go_pack())
    _DEFAULT_PACKS_REGISTERED = True


# @grace.anchor grace.spec_registry._build_python_pack
# @grace.complexity 5
def _build_python_pack() -> GraceLanguagePack:
    from tree_sitter_python import language as language_python

    from grace.models import BlockKind
    from grace.treesitter_base import TreeSitterBlockQuerySpec, TreeSitterLanguageSpec

    def spec_factory() -> TreeSitterLanguageSpec:
        return TreeSitterLanguageSpec(
            language_name="python",
            file_extensions=(".py",),
            language_factory=language_python,
            line_comment_prefixes=("#",),
            block_query_specs=(
                TreeSitterBlockQuerySpec(
                    query="(module (decorated_definition definition: (function_definition name: (identifier) @name) @block) @line_start)",
                    kind=BlockKind.FUNCTION,
                    symbol_capture="name",
                    block_capture="block",
                    line_start_capture="line_start",
                    promote_async_kind=BlockKind.ASYNC_FUNCTION,
                ),
                TreeSitterBlockQuerySpec(
                    query="(module (function_definition name: (identifier) @name) @block)",
                    kind=BlockKind.FUNCTION,
                    symbol_capture="name",
                    block_capture="block",
                    promote_async_kind=BlockKind.ASYNC_FUNCTION,
                ),
                TreeSitterBlockQuerySpec(
                    query="(module (decorated_definition definition: (class_definition name: (identifier) @name) @block) @line_start)",
                    kind=BlockKind.CLASS,
                    symbol_capture="name",
                    line_start_capture="line_start",
                ),
                TreeSitterBlockQuerySpec(
                    query="(module (class_definition name: (identifier) @name) @block)",
                    kind=BlockKind.CLASS,
                    symbol_capture="name",
                ),
                TreeSitterBlockQuerySpec(
                    query="(class_definition name: (identifier) @owner body: (block (decorated_definition definition: (function_definition name: (identifier) @name) @block) @line_start))",
                    kind=BlockKind.METHOD,
                    symbol_capture="name",
                    owner_capture="owner",
                    line_start_capture="line_start",
                    qualified_name_template="{owner_name}.{symbol_name}",
                ),
                TreeSitterBlockQuerySpec(
                    query="(class_definition name: (identifier) @owner body: (block (function_definition name: (identifier) @name) @block))",
                    kind=BlockKind.METHOD,
                    symbol_capture="name",
                    owner_capture="owner",
                    qualified_name_template="{owner_name}.{symbol_name}",
                ),
            ),
        )

    return build_treesitter_pack(
        language_name="python",
        file_extensions=(".py",),
        status=GraceLanguagePackStatus.REFERENCE,
        spec_factory=spec_factory,
        adapter_factory=lambda: __import__("grace.python_adapter", fromlist=["PythonAdapter"]).PythonAdapter(),
    )


# @grace.anchor grace.spec_registry._build_typescript_pack
# @grace.complexity 6
# @grace.belief TypeScript should absorb frontend-specific construct growth declaratively, so TSX and future shapes land as mergeable construct packs instead of wrapper-local AST logic.
def _build_typescript_pack() -> GraceLanguagePack:
    from tree_sitter_typescript import language_typescript

    from grace.construct_pack import apply_construct_packs
    from grace.construct_registry import get_construct_packs
    from grace.models import BlockKind
    from grace.treesitter_base import TreeSitterBlockQuerySpec, TreeSitterLanguageSpec

    def base_spec_factory() -> TreeSitterLanguageSpec:
        return TreeSitterLanguageSpec(
            language_name="typescript",
            file_extensions=(".ts",),
            language_factory=language_typescript,
            line_comment_prefixes=("//",),
            block_comment_delimiters=(("/*", "*/"),),
            block_query_specs=(
                TreeSitterBlockQuerySpec(
                    query="(program (function_declaration name: (identifier) @name) @block)",
                    kind=BlockKind.FUNCTION,
                    symbol_capture="name",
                    promote_async_kind=BlockKind.ASYNC_FUNCTION,
                ),
                TreeSitterBlockQuerySpec(
                    query="(program (lexical_declaration (variable_declarator name: (identifier) @name value: (arrow_function) @block)))",
                    kind=BlockKind.FUNCTION,
                    symbol_capture="name",
                    promote_async_kind=BlockKind.ASYNC_FUNCTION,
                    line_start_capture="block",
                ),
                TreeSitterBlockQuerySpec(
                    query="(program (class_declaration name: (type_identifier) @name) @block)",
                    kind=BlockKind.CLASS,
                    symbol_capture="name",
                ),
                TreeSitterBlockQuerySpec(
                    query="(class_declaration name: (type_identifier) @owner body: (class_body (method_definition name: (property_identifier) @name) @block))",
                    kind=BlockKind.METHOD,
                    symbol_capture="name",
                    owner_capture="owner",
                    qualified_name_template="{owner_name}.{symbol_name}",
                ),
                TreeSitterBlockQuerySpec(
                    query="(program (lexical_declaration (variable_declarator name: (identifier) @owner value: (object (method_definition name: (property_identifier) @name) @block))))",
                    kind=BlockKind.METHOD,
                    symbol_capture="name",
                    owner_capture="owner",
                    qualified_name_template="{owner_name}.{symbol_name}",
                ),
            ),
        )

    construct_packs = get_construct_packs("typescript")
    construct_pack_names = tuple(pack.pack_name for pack in construct_packs)

    def spec_factory() -> TreeSitterLanguageSpec:
        return apply_construct_packs(base_spec_factory(), construct_packs)

    merged_spec = spec_factory()
    bootstrap_safe = all(pack.bootstrap_safe is not False for pack in construct_packs)

    return build_treesitter_pack(
        language_name="typescript",
        file_extensions=merged_spec.file_extensions,
        status=GraceLanguagePackStatus.PILOT,
        spec_factory=spec_factory,
        adapter_factory=lambda: __import__("grace.typescript_adapter", fromlist=["TypeScriptAdapter"]).TypeScriptAdapter(),
        bootstrap_safe=bootstrap_safe,
        construct_pack_names=construct_pack_names,
    )


# @grace.anchor grace.spec_registry._build_go_pack
# @grace.complexity 5
def _build_go_pack() -> GraceLanguagePack:
    from tree_sitter_go import language as language_go

    from grace.models import BlockKind
    from grace.treesitter_base import TreeSitterBlockQuerySpec, TreeSitterLanguageSpec

    def spec_factory() -> TreeSitterLanguageSpec:
        return TreeSitterLanguageSpec(
            language_name="go",
            file_extensions=(".go",),
            language_factory=language_go,
            line_comment_prefixes=("//",),
            block_query_specs=(
                TreeSitterBlockQuerySpec(
                    query="(source_file (function_declaration name: (identifier) @name) @block)",
                    kind=BlockKind.FUNCTION,
                    symbol_capture="name",
                ),
                TreeSitterBlockQuerySpec(
                    query="(source_file (method_declaration receiver: (parameter_list (parameter_declaration type: (pointer_type (type_identifier) @owner))) name: (field_identifier) @name) @block)",
                    kind=BlockKind.METHOD,
                    symbol_capture="name",
                    owner_capture="owner",
                    qualified_name_template="{owner_name}.{symbol_name}",
                ),
                TreeSitterBlockQuerySpec(
                    query="(source_file (method_declaration receiver: (parameter_list (parameter_declaration type: (type_identifier) @owner)) name: (field_identifier) @name) @block)",
                    kind=BlockKind.METHOD,
                    symbol_capture="name",
                    owner_capture="owner",
                    qualified_name_template="{owner_name}.{symbol_name}",
                ),
                TreeSitterBlockQuerySpec(
                    query="(source_file (type_declaration (type_spec name: (type_identifier) @name type: (struct_type)) @block))",
                    kind=BlockKind.CLASS,
                    symbol_capture="name",
                ),
            ),
        )

    return build_treesitter_pack(
        language_name="go",
        file_extensions=(".go",),
        status=GraceLanguagePackStatus.PILOT,
        spec_factory=spec_factory,
        adapter_factory=lambda: __import__("grace.go_adapter", fromlist=["GoAdapter"]).GoAdapter(),
    )


__all__ = [
    "get_language_pack",
    "get_language_pack_for_path",
    "get_registered_language_packs",
    "register_language_pack",
]
