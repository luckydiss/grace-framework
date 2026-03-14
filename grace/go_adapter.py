# @grace.module grace.go_adapter
# @grace.purpose Implement a minimal Go language adapter that proves GRACE adapter architecture scales to a third language without changing core semantics.
# @grace.interfaces GoAdapter.discover_annotations(source_text)->tuple[str, ...]; GoAdapter.extract_module_metadata(parsed_file)->GraceModuleMetadata; GoAdapter.extract_blocks(parsed_file)->tuple[GraceBlockMetadata, ...]; GoAdapter.compute_block_span(block)->tuple[int, int]; GoAdapter.build_grace_file_model(file_path)->GraceFileModel
# @grace.invariant The Go adapter remains intentionally narrow: module annotations, function declarations, receiver methods, and simple struct type declarations.
# @grace.invariant Unsupported Go constructs must remain inert unless GRACE annotations attempt to bind to them, in which case parsing fails predictably.
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from grace.language_adapter import GraceLanguageAdapter
from grace.models import BlockKind, GraceBlockMetadata, GraceParseIssue

LINE_ANNOTATION_RE = re.compile(r"^\s*//\s*@grace\.(?P<name>[a-z_]+)(?:\s+(?P<payload>.*\S))?\s*$")
FUNC_DECL_RE = re.compile(
    r"^\s*func\s*(?:\((?P<receiver>[^)]*)\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]+\])?\s*\("
)
TYPE_DECL_RE = re.compile(r"^\s*type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+struct\b")


# @grace.anchor grace.go_adapter.GoAdapter
# @grace.complexity 4
# @grace.belief Go should now resolve through the same declarative pack registry as Python and TypeScript so scaling to further languages means adding pack metadata rather than new hard-coded dispatch and wrapper setup.
# @grace.links grace.spec_registry.get_language_pack
class GoAdapter(GraceLanguageAdapter):
    language_name = "go"
    file_extensions = (".go",)

    def __init__(self) -> None:
        from grace.spec_registry import get_language_pack

        self._base = get_language_pack("go").base_adapter_factory()
        self.language_name = self._base.language_name
        self.file_extensions = self._base.file_extensions

    # @grace.anchor grace.go_adapter.GoAdapter.discover_annotations
    # @grace.complexity 2
    def discover_annotations(self, source_text: str) -> tuple[str, ...]:
        return self._base.discover_annotations(source_text)

    # @grace.anchor grace.go_adapter.GoAdapter.extract_module_metadata
    # @grace.complexity 2
    def extract_module_metadata(self, parsed_file: Any):
        return self._base.extract_module_metadata(parsed_file)

    # @grace.anchor grace.go_adapter.GoAdapter.extract_blocks
    # @grace.complexity 2
    def extract_blocks(self, parsed_file: Any) -> tuple[GraceBlockMetadata, ...]:
        return self._base.extract_blocks(parsed_file)

    # @grace.anchor grace.go_adapter.GoAdapter.compute_block_span
    # @grace.complexity 1
    def compute_block_span(self, block: GraceBlockMetadata) -> tuple[int, int]:
        return self._base.compute_block_span(block)

    # @grace.anchor grace.go_adapter.GoAdapter.build_grace_file_model
    # @grace.complexity 6
    # @grace.belief Go should now resolve through the same declarative pack registry as Python and TypeScript so scaling to further languages means adding pack metadata rather than new hard-coded dispatch and wrapper setup.
    # @grace.links grace.spec_registry.get_language_pack
    def build_grace_file_model(self, file_path: str | Path):
        return self._base.build_grace_file_model(file_path)


# @grace.anchor grace.go_adapter._collect_definition_targets
# @grace.complexity 6
# @grace.belief The Go pilot scans only top-level declarations and receiver methods; keeping target collection line-oriented and deterministic is enough for a minimal third-language proof without pretending to cover broader Go syntax.
def _collect_definition_targets(lines: list[str]) -> dict[int, object]:
    from grace import parser as parser_module

    targets: dict[int, object] = {}
    line_count = len(lines)
    index = 0
    while index < line_count:
        line_number = index + 1
        raw_line = lines[index]

        type_match = TYPE_DECL_RE.match(raw_line)
        if type_match:
            type_name = type_match.group("name")
            targets.setdefault(
                line_number,
                parser_module._DefinitionTarget(
                    kind=BlockKind.CLASS,
                    symbol_name=type_name,
                    qualified_name=type_name,
                    is_async=False,
                    line_start=line_number,
                    line_end=_compute_block_end(lines, index),
                ),
            )
            index += 1
            continue

        function_match = FUNC_DECL_RE.match(raw_line)
        if function_match:
            receiver = function_match.group("receiver")
            symbol_name = function_match.group("name")
            receiver_type = _parse_receiver_type(receiver) if receiver else None
            kind = BlockKind.METHOD if receiver_type else BlockKind.FUNCTION
            qualified_name = f"{receiver_type}.{symbol_name}" if receiver_type else symbol_name
            targets.setdefault(
                line_number,
                parser_module._DefinitionTarget(
                    kind=kind,
                    symbol_name=symbol_name,
                    qualified_name=qualified_name,
                    is_async=False,
                    line_start=line_number,
                    line_end=_compute_block_end(lines, index),
                ),
            )

        index += 1

    return targets


# @grace.anchor grace.go_adapter._compute_block_end
# @grace.complexity 4
def _compute_block_end(lines: list[str], start_index: int) -> int:
    brace_depth = 0
    seen_open_brace = False
    for index in range(start_index, len(lines)):
        line = lines[index]
        brace_depth += line.count("{")
        if "{" in line:
            seen_open_brace = True
        brace_depth -= line.count("}")
        if seen_open_brace and brace_depth <= 0:
            return index + 1
    return start_index + 1


# @grace.anchor grace.go_adapter._parse_receiver_type
# @grace.complexity 3
def _parse_receiver_type(receiver_text: str) -> str:
    tokens = [token for token in receiver_text.replace("*", " ").split() if token]
    if not tokens:
        return ""
    return tokens[-1]


# @grace.anchor grace.go_adapter._match_annotation_line
# @grace.complexity 1
def _match_annotation_line(raw_line: str) -> tuple[str, str] | None:
    match = LINE_ANNOTATION_RE.match(raw_line)
    if match is None:
        return None
    return match.group("name"), (match.group("payload") or "").strip()


# @grace.anchor grace.go_adapter._is_comment_like_line
# @grace.complexity 1
def _is_comment_like_line(raw_line: str) -> bool:
    return raw_line.strip().startswith("//")


__all__ = ["GoAdapter"]
