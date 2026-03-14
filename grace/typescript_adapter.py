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
# @grace.complexity 4
# @grace.belief TypeScript should now reuse a registry-backed pack so future construct growth stays inside declarative specs rather than reintroducing wrapper-local parser configuration drift.
# @grace.links grace.spec_registry.get_language_pack
class TypeScriptAdapter(GraceLanguageAdapter):
    language_name = "typescript"
    file_extensions = (".ts",)

    def __init__(self) -> None:
        from grace.spec_registry import get_language_pack

        self._base = get_language_pack("typescript").base_adapter_factory()
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
    # @grace.belief TypeScript should now reuse a registry-backed pack so future construct growth stays inside declarative specs rather than reintroducing wrapper-local parser configuration drift.
    # @grace.links grace.spec_registry.get_language_pack
    def build_grace_file_model(self, file_path: str | Path):
        return self._base.build_grace_file_model(file_path)


# @grace.anchor grace.typescript_adapter._collect_definition_targets
# @grace.complexity 2
# @grace.belief The TypeScript adapter no longer performs handwritten AST traversal. Legacy helper anchors stay only as explicit fail-fast shims so all runtime parsing flows through the declarative TreeSitterAdapterBase path.
# @grace.links grace.typescript_adapter.TypeScriptAdapter, grace.treesitter_base.TreeSitterAdapterBase
def _collect_definition_targets(parsed_source: TreeSitterSourceFile) -> dict[int, object]:
    raise RuntimeError(
        "legacy TypeScript traversal helpers were removed; use TypeScriptAdapter via TreeSitterAdapterBase"
    )


# @grace.anchor grace.typescript_adapter._build_function_target
# @grace.complexity 1
def _build_function_target(source_bytes: bytes, node: Node):
    raise RuntimeError(
        "legacy TypeScript traversal helpers were removed; use TypeScriptAdapter via TreeSitterAdapterBase"
    )


# @grace.anchor grace.typescript_adapter._build_arrow_function_target
# @grace.complexity 1
def _build_arrow_function_target(source_bytes: bytes, symbol_name: str, node: Node, *, binding_line_start: int):
    raise RuntimeError(
        "legacy TypeScript traversal helpers were removed; use TypeScriptAdapter via TreeSitterAdapterBase"
    )


# @grace.anchor grace.typescript_adapter._build_class_target
# @grace.complexity 1
def _build_class_target(source_bytes: bytes, node: Node):
    raise RuntimeError(
        "legacy TypeScript traversal helpers were removed; use TypeScriptAdapter via TreeSitterAdapterBase"
    )


# @grace.anchor grace.typescript_adapter._build_method_target
# @grace.complexity 1
def _build_method_target(source_bytes: bytes, class_name: str, node: Node):
    raise RuntimeError(
        "legacy TypeScript traversal helpers were removed; use TypeScriptAdapter via TreeSitterAdapterBase"
    )


# @grace.anchor grace.typescript_adapter._build_object_method_target
# @grace.complexity 1
def _build_object_method_target(source_bytes: bytes, object_name: str, node: Node):
    raise RuntimeError(
        "legacy TypeScript traversal helpers were removed; use TypeScriptAdapter via TreeSitterAdapterBase"
    )


# @grace.anchor grace.typescript_adapter._match_annotation_line
# @grace.complexity 1
def _match_annotation_line(raw_line: str) -> tuple[str, str] | None:
    raise RuntimeError(
        "legacy TypeScript traversal helpers were removed; use TypeScriptAdapter via TreeSitterAdapterBase"
    )


# @grace.anchor grace.typescript_adapter._is_comment_like_line
# @grace.complexity 1
def _is_comment_like_line(raw_line: str) -> bool:
    raise RuntimeError(
        "legacy TypeScript traversal helpers were removed; use TypeScriptAdapter via TreeSitterAdapterBase"
    )


# @grace.anchor grace.typescript_adapter._node_text
# @grace.complexity 1
def _node_text(source_bytes: bytes, node: Node | None) -> str:
    raise RuntimeError(
        "legacy TypeScript traversal helpers were removed; use TypeScriptAdapter via TreeSitterAdapterBase"
    )


__all__ = ["TypeScriptAdapter"]
