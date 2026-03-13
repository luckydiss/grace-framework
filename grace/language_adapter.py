# @grace.module grace.language_adapter
# @grace.purpose Define the language adapter contract that lets GRACE parse annotated files through language-specific integrations while keeping core semantics unchanged.
# @grace.interfaces GraceLanguageAdapter.discover_annotations(source_text)->tuple[str, ...]; GraceLanguageAdapter.extract_module_metadata(parsed_file)->GraceModuleMetadata; GraceLanguageAdapter.extract_blocks(parsed_file)->tuple[GraceBlockMetadata, ...]; GraceLanguageAdapter.compute_block_span(block)->tuple[int, int]; GraceLanguageAdapter.build_grace_file_model(file_path)->GraceFileModel; get_language_adapter_for_path(path)->GraceLanguageAdapter
# @grace.invariant Language adapters may specialize syntax parsing and block binding, but they must emit GraceFileModel-compatible data for core layers.
# @grace.invariant Adapter selection is derived from file path and must never override inline GRACE annotations as the source of truth.
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import sys
from typing import Any

from grace.models import GraceBlockMetadata, GraceFileModel, GraceModuleMetadata


_PYTHON_ADAPTER_CLASS: type["GraceLanguageAdapter"] | None = None


# @grace.anchor grace.language_adapter.GraceLanguageAdapter
# @grace.complexity 3
class GraceLanguageAdapter(ABC):
    language_name: str
    file_extensions: tuple[str, ...]

    # @grace.anchor grace.language_adapter.GraceLanguageAdapter.discover_annotations
    # @grace.complexity 2
    @abstractmethod
    def discover_annotations(self, source_text: str) -> tuple[str, ...]:
        raise NotImplementedError

    # @grace.anchor grace.language_adapter.GraceLanguageAdapter.extract_module_metadata
    # @grace.complexity 2
    @abstractmethod
    def extract_module_metadata(self, parsed_file: Any) -> GraceModuleMetadata:
        raise NotImplementedError

    # @grace.anchor grace.language_adapter.GraceLanguageAdapter.extract_blocks
    # @grace.complexity 2
    @abstractmethod
    def extract_blocks(self, parsed_file: Any) -> tuple[GraceBlockMetadata, ...]:
        raise NotImplementedError

    # @grace.anchor grace.language_adapter.GraceLanguageAdapter.compute_block_span
    # @grace.complexity 2
    @abstractmethod
    def compute_block_span(self, block: GraceBlockMetadata) -> tuple[int, int]:
        raise NotImplementedError

    # @grace.anchor grace.language_adapter.GraceLanguageAdapter.build_grace_file_model
    # @grace.complexity 3
    @abstractmethod
    def build_grace_file_model(self, file_path: str | Path) -> GraceFileModel:
        raise NotImplementedError


# @grace.anchor grace.language_adapter.get_language_adapter_for_path
# @grace.complexity 3
# @grace.belief Adapter dispatch should remain intentionally simple until a second runtime language exists; suffix-based routing keeps parser entrypoints language-agnostic without introducing speculative auto-detection.
def get_language_adapter_for_path(path: str | Path) -> GraceLanguageAdapter:
    source_path = Path(path)
    suffix = source_path.suffix.lower()

    if suffix == ".py":
        global _PYTHON_ADAPTER_CLASS
        if _PYTHON_ADAPTER_CLASS is None:
            from grace.python_adapter import PythonAdapter

            _PYTHON_ADAPTER_CLASS = PythonAdapter

        return _PYTHON_ADAPTER_CLASS()

    raise ValueError(f"no GRACE language adapter is registered for {suffix or '<no suffix>'}")


# @grace.anchor grace.language_adapter._register_python_adapter
# @grace.complexity 1
def _register_python_adapter(adapter_cls: type[GraceLanguageAdapter]) -> None:
    global _PYTHON_ADAPTER_CLASS
    _PYTHON_ADAPTER_CLASS = adapter_cls


_parser_module = sys.modules.get("grace.parser")
if _parser_module is not None:
    setattr(_parser_module, "_grace_language_adapter_module", sys.modules[__name__])


__all__ = ["GraceLanguageAdapter", "get_language_adapter_for_path"]
