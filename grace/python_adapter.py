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
# @grace.complexity 4
# @grace.belief Python should now consume the same registry-backed declarative pack path as the other adapters so adding or refining language support means editing pack metadata rather than hard-coding another wrapper-local spec.
# @grace.links grace.spec_registry.get_language_pack
class PythonAdapter(GraceLanguageAdapter):
    language_name = "python"
    file_extensions = (".py",)

    def __init__(self) -> None:
        from grace.spec_registry import get_language_pack

        self._base = get_language_pack("python").base_adapter_factory()
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
    # @grace.belief Python should now consume the same registry-backed declarative pack path as the other adapters so adding or refining language support means editing pack metadata rather than hard-coding another wrapper-local spec.
    # @grace.links grace.spec_registry.get_language_pack
    def build_grace_file_model(self, file_path: str | Path):
        return self._base.build_grace_file_model(file_path)


from grace.language_adapter import _register_python_adapter

_register_python_adapter(PythonAdapter)


__all__ = ["PythonAdapter"]
