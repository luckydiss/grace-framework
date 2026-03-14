# @grace.module grace.python_adapter
# @grace.purpose Implement the reference Python language adapter that parses inline GRACE annotations and emits GraceFileModel data without changing core semantics.
# @grace.interfaces PythonAdapter.discover_annotations(source_text)->tuple[str, ...]; PythonAdapter.extract_module_metadata(parsed_file)->GraceModuleMetadata; PythonAdapter.extract_blocks(parsed_file)->tuple[GraceBlockMetadata, ...]; PythonAdapter.compute_block_span(block)->tuple[int, int]; PythonAdapter.build_grace_file_model(file_path)->GraceFileModel
# @grace.invariant Python remains the reference adapter; behavior must stay identical to the pre-adapter parser baseline.
# @grace.invariant Python adapter output must remain fully compatible with validator, linter, map, query, impact, read, planner, patcher, and CLI contracts.
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from grace.language_adapter import GraceLanguageAdapter
from grace.models import GraceBlockMetadata, GraceParseIssue, ParseErrorCode


# @grace.anchor grace.python_adapter.PythonAdapter
# @grace.complexity 6
# @grace.belief Python should share the declarative Tree-sitter execution path with the other adapters, but decorated definitions must still bind to the underlying function or class node so async promotion and line spans remain correct.
# @grace.links grace.treesitter_base.TreeSitterAdapterBase
class PythonAdapter(GraceLanguageAdapter):
    language_name = "python"
    file_extensions = (".py",)

    def __init__(self) -> None:
        from tree_sitter_python import language as language_python

        from grace.models import BlockKind
        from grace.treesitter_base import (
            TreeSitterAdapterBase,
            TreeSitterBlockQuerySpec,
            TreeSitterLanguageSpec,
        )

        spec = TreeSitterLanguageSpec(
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
        self._base = TreeSitterAdapterBase(spec)
        self.language_name = self._base.language_name
        self.file_extensions = self._base.file_extensions

    # @grace.anchor grace.python_adapter.PythonAdapter.discover_annotations
    # @grace.complexity 2
    def discover_annotations(self, source_text: str) -> tuple[str, ...]:
        return self._base.discover_annotations(source_text)

    # @grace.anchor grace.python_adapter.PythonAdapter.extract_module_metadata
    # @grace.complexity 2
    def extract_module_metadata(self, parsed_file: Any):
        return self._base.extract_module_metadata(parsed_file)

    # @grace.anchor grace.python_adapter.PythonAdapter.extract_blocks
    # @grace.complexity 2
    def extract_blocks(self, parsed_file: Any) -> tuple[GraceBlockMetadata, ...]:
        return self._base.extract_blocks(parsed_file)

    # @grace.anchor grace.python_adapter.PythonAdapter.compute_block_span
    # @grace.complexity 2
    def compute_block_span(self, block: GraceBlockMetadata) -> tuple[int, int]:
        return self._base.compute_block_span(block)

    # @grace.anchor grace.python_adapter.PythonAdapter.build_grace_file_model
    # @grace.complexity 6
    # @grace.belief Python now exercises the same declarative Tree-sitter execution path as other adapters so future languages can be added by spec instead of by copying parser loops.
    # @grace.links grace.treesitter_base.TreeSitterAdapterBase
    def build_grace_file_model(self, file_path: str | Path):
        return self._base.build_grace_file_model(file_path)


from grace.language_adapter import _register_python_adapter

_register_python_adapter(PythonAdapter)


__all__ = ["PythonAdapter"]
