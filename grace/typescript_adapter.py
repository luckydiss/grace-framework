# @grace.module grace.typescript_adapter
# @grace.purpose Implement the pilot TypeScript language adapter using Tree-sitter as parsing substrate while preserving GRACE core semantics.
# @grace.interfaces TypeScriptAdapter.discover_annotations(source_text)->tuple[str, ...]; TypeScriptAdapter.extract_module_metadata(parsed_file)->GraceModuleMetadata; TypeScriptAdapter.extract_blocks(parsed_file)->tuple[GraceBlockMetadata, ...]; TypeScriptAdapter.compute_block_span(block)->tuple[int, int]; TypeScriptAdapter.build_grace_file_model(file_path)->GraceFileModel
# @grace.invariant The TypeScript adapter remains a pilot: it only supports module annotations plus function, async function, class, and method blocks.
# @grace.invariant Tree-sitter is substrate only; the adapter must still emit GraceFileModel-compatible data for all core layers.
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from tree_sitter import Node
from tree_sitter_typescript import language_typescript

from grace.language_adapter import GraceLanguageAdapter
from grace.models import BlockKind, GraceBlockMetadata, GraceParseIssue
from grace.tree_sitter_adapter import TreeSitterSourceFile, iter_tree_nodes, load_tree_sitter_source

LINE_ANNOTATION_RE = re.compile(r"^\s*//\s*@grace\.(?P<name>[a-z_]+)(?:\s+(?P<payload>.*\S))?\s*$")
BLOCK_ANNOTATION_RE = re.compile(r"^\s*/\*\s*@grace\.(?P<name>[a-z_]+)(?:\s+(?P<payload>.*\S))?\s*\*/\s*$")


# @grace.anchor grace.typescript_adapter.TypeScriptAdapter
# @grace.complexity 6
# @grace.belief TypeScript should stop owning its own annotation state machine and instead supply a declarative Tree-sitter spec so the adapter boundary scales to more languages without duplicating parser loops.
# @grace.links grace.treesitter_base.TreeSitterAdapterBase, grace.treesitter_base.TreeSitterLanguageSpec
class TypeScriptAdapter(GraceLanguageAdapter):
    language_name = "typescript"
    file_extensions = (".ts",)

    def __init__(self) -> None:
        from tree_sitter_typescript import language_typescript

        from grace.treesitter_base import (
            TreeSitterAdapterBase,
            TreeSitterBlockQuerySpec,
            TreeSitterLanguageSpec,
        )

        spec = TreeSitterLanguageSpec(
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
        self._base = TreeSitterAdapterBase(spec)
        self.language_name = self._base.language_name
        self.file_extensions = self._base.file_extensions

    # @grace.anchor grace.typescript_adapter.TypeScriptAdapter.discover_annotations
    # @grace.complexity 2
    def discover_annotations(self, source_text: str) -> tuple[str, ...]:
        return self._base.discover_annotations(source_text)

    # @grace.anchor grace.typescript_adapter.TypeScriptAdapter.extract_module_metadata
    # @grace.complexity 2
    def extract_module_metadata(self, parsed_file: Any):
        return self._base.extract_module_metadata(parsed_file)

    # @grace.anchor grace.typescript_adapter.TypeScriptAdapter.extract_blocks
    # @grace.complexity 2
    def extract_blocks(self, parsed_file: Any) -> tuple[GraceBlockMetadata, ...]:
        return self._base.extract_blocks(parsed_file)

    # @grace.anchor grace.typescript_adapter.TypeScriptAdapter.compute_block_span
    # @grace.complexity 1
    def compute_block_span(self, block: GraceBlockMetadata) -> tuple[int, int]:
        return self._base.compute_block_span(block)

    # @grace.anchor grace.typescript_adapter.TypeScriptAdapter.build_grace_file_model
    # @grace.complexity 6
    # @grace.belief TypeScript now participates in the same data-driven Tree-sitter engine as Python and Go, so extending coverage becomes a matter of query specs instead of handwritten parser loops.
    # @grace.links grace.treesitter_base.TreeSitterAdapterBase
    def build_grace_file_model(self, file_path: str | Path):
        return self._base.build_grace_file_model(file_path)


# @grace.anchor grace.typescript_adapter._collect_definition_targets
# @grace.complexity 5
# @grace.links grace.tree_sitter_adapter.iter_tree_nodes, grace.typescript_adapter._build_arrow_function_target, grace.typescript_adapter._build_object_method_target
def _collect_definition_targets(parsed_source: TreeSitterSourceFile) -> dict[int, object]:
    from grace import parser as parser_module

    targets: dict[int, object] = {}
    for node in iter_tree_nodes(parsed_source.tree.root_node):
        if node.type == "function_declaration":
            target = _build_function_target(parsed_source.source_bytes, node)
            targets.setdefault(target.line_start, target)
            continue

        if node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            if name_node is None or value_node is None:
                continue

            symbol_name = _node_text(parsed_source.source_bytes, name_node)
            if value_node.type == "arrow_function":
                target = _build_arrow_function_target(
                    parsed_source.source_bytes,
                    symbol_name,
                    value_node,
                    binding_line_start=node.start_point.row + 1,
                )
                targets.setdefault(target.line_start, target)
                continue

            if value_node.type != "object":
                continue

            for child in value_node.children:
                if child.type != "method_definition":
                    continue
                target = _build_object_method_target(parsed_source.source_bytes, symbol_name, child)
                targets.setdefault(target.line_start, target)
            continue

        if node.type != "class_declaration":
            continue

        class_target = _build_class_target(parsed_source.source_bytes, node)
        targets.setdefault(class_target.line_start, class_target)

        class_name = class_target.symbol_name
        class_body = node.child_by_field_name("body")
        if class_body is None:
            continue

        for child in class_body.children:
            if child.type != "method_definition":
                continue
            target = _build_method_target(parsed_source.source_bytes, class_name, child)
            targets.setdefault(target.line_start, target)

    return targets


# @grace.anchor grace.typescript_adapter._build_function_target
# @grace.complexity 3
def _build_function_target(source_bytes: bytes, node: Node):
    from grace import parser as parser_module

    name_node = node.child_by_field_name("name")
    symbol_name = _node_text(source_bytes, name_node)
    is_async = any(child.type == "async" for child in node.children)
    kind = BlockKind.ASYNC_FUNCTION if is_async else BlockKind.FUNCTION
    return parser_module._DefinitionTarget(
        kind=kind,
        symbol_name=symbol_name,
        qualified_name=symbol_name,
        is_async=is_async,
        line_start=node.start_point.row + 1,
        line_end=node.end_point.row + 1,
    )


# @grace.anchor grace.typescript_adapter._build_arrow_function_target
# @grace.complexity 3
def _build_arrow_function_target(source_bytes: bytes, symbol_name: str, node: Node, *, binding_line_start: int):
    from grace import parser as parser_module

    is_async = any(child.type == "async" for child in node.children)
    kind = BlockKind.ASYNC_FUNCTION if is_async else BlockKind.FUNCTION
    return parser_module._DefinitionTarget(
        kind=kind,
        symbol_name=symbol_name,
        qualified_name=symbol_name,
        is_async=is_async,
        line_start=binding_line_start,
        line_end=node.end_point.row + 1,
    )


# @grace.anchor grace.typescript_adapter._build_class_target
# @grace.complexity 2
def _build_class_target(source_bytes: bytes, node: Node):
    from grace import parser as parser_module

    name_node = node.child_by_field_name("name")
    class_name = _node_text(source_bytes, name_node)
    return parser_module._DefinitionTarget(
        kind=BlockKind.CLASS,
        symbol_name=class_name,
        qualified_name=class_name,
        is_async=False,
        line_start=node.start_point.row + 1,
        line_end=node.end_point.row + 1,
    )


# @grace.anchor grace.typescript_adapter._build_method_target
# @grace.complexity 3
def _build_method_target(source_bytes: bytes, class_name: str, node: Node):
    from grace import parser as parser_module

    name_node = node.child_by_field_name("name")
    method_name = _node_text(source_bytes, name_node)
    is_async = any(child.type == "async" for child in node.children)
    return parser_module._DefinitionTarget(
        kind=BlockKind.METHOD,
        symbol_name=method_name,
        qualified_name=f"{class_name}.{method_name}",
        is_async=is_async,
        line_start=node.start_point.row + 1,
        line_end=node.end_point.row + 1,
    )


# @grace.anchor grace.typescript_adapter._build_object_method_target
# @grace.complexity 3
def _build_object_method_target(source_bytes: bytes, object_name: str, node: Node):
    from grace import parser as parser_module

    name_node = node.child_by_field_name("name")
    method_name = _node_text(source_bytes, name_node)
    is_async = any(child.type == "async" for child in node.children)
    return parser_module._DefinitionTarget(
        kind=BlockKind.METHOD,
        symbol_name=method_name,
        qualified_name=f"{object_name}.{method_name}",
        is_async=is_async,
        line_start=node.start_point.row + 1,
        line_end=node.end_point.row + 1,
    )


# @grace.anchor grace.typescript_adapter._match_annotation_line
# @grace.complexity 2
def _match_annotation_line(raw_line: str) -> tuple[str, str] | None:
    line_match = LINE_ANNOTATION_RE.match(raw_line)
    if line_match:
        return line_match.group("name"), (line_match.group("payload") or "").strip()

    block_match = BLOCK_ANNOTATION_RE.match(raw_line)
    if block_match:
        return block_match.group("name"), (block_match.group("payload") or "").strip()

    return None


# @grace.anchor grace.typescript_adapter._is_comment_like_line
# @grace.complexity 2
def _is_comment_like_line(raw_line: str) -> bool:
    stripped = raw_line.strip()
    return stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith("*/")


# @grace.anchor grace.typescript_adapter._node_text
# @grace.complexity 1
def _node_text(source_bytes: bytes, node: Node | None) -> str:
    if node is None:
        return ""
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8")


__all__ = ["TypeScriptAdapter"]
