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
# @grace.complexity 5
class GoAdapter(GraceLanguageAdapter):
    language_name = "go"
    file_extensions = (".go",)

    # @grace.anchor grace.go_adapter.GoAdapter.discover_annotations
    # @grace.complexity 2
    def discover_annotations(self, source_text: str) -> tuple[str, ...]:
        discovered: list[str] = []
        for raw_line in source_text.splitlines():
            match = _match_annotation_line(raw_line)
            if match is not None:
                discovered.append(match[0])
        return tuple(discovered)

    # @grace.anchor grace.go_adapter.GoAdapter.extract_module_metadata
    # @grace.complexity 2
    def extract_module_metadata(self, parsed_file: Any):
        from grace.models import GraceModuleMetadata

        module = parsed_file["module"]
        return GraceModuleMetadata(
            module_id=module.module_id or "",
            purpose=module.purpose or "",
            interfaces=module.interfaces or "",
            invariants=tuple(module.invariants),
        )

    # @grace.anchor grace.go_adapter.GoAdapter.extract_blocks
    # @grace.complexity 2
    def extract_blocks(self, parsed_file: Any) -> tuple[GraceBlockMetadata, ...]:
        return tuple(parsed_file["blocks"])

    # @grace.anchor grace.go_adapter.GoAdapter.compute_block_span
    # @grace.complexity 1
    def compute_block_span(self, block: GraceBlockMetadata) -> tuple[int, int]:
        return (block.line_start, block.line_end)

    # @grace.anchor grace.go_adapter.GoAdapter.build_grace_file_model
    # @grace.complexity 7
    # @grace.belief The Go pilot adapter should reuse the existing GRACE module and block annotation state machine so the only language-specific logic lives in deterministic target discovery and span extraction.
    # @grace.links grace.go_adapter._collect_definition_targets
    def build_grace_file_model(self, file_path: str | Path):
        from grace import parser as parser_module
        from grace.models import GraceFileModel

        source_path = Path(file_path)
        source_text = source_path.read_text(encoding="utf-8")
        lines = source_text.splitlines()
        definition_targets = _collect_definition_targets(lines)

        errors: list[GraceParseIssue] = []
        module = parser_module._ModuleAccumulator()
        blocks: list[GraceBlockMetadata] = []
        pending_block: parser_module._PendingBlock | None = None
        block_section_started = False
        seen_anchor_ids: set[str] = set()

        for line_number, raw_line in enumerate(lines, start=1):
            matched_annotation = _match_annotation_line(raw_line)
            stripped = raw_line.strip()

            if matched_annotation is not None:
                annotation_name, payload = matched_annotation
                if annotation_name in parser_module.MODULE_ANNOTATIONS:
                    if block_section_started:
                        errors.append(
                            GraceParseIssue(
                                code=parser_module.ParseErrorCode.MODULE_ANNOTATION_AFTER_BLOCKS,
                                message=f"@grace.{annotation_name} is not allowed after block declarations start",
                                line=line_number,
                            )
                        )
                        continue
                    parser_module._consume_module_annotation(module, annotation_name, payload, line_number, errors)
                    continue

                if annotation_name in parser_module.BLOCK_ANNOTATIONS:
                    block_section_started = True
                    pending_block = parser_module._consume_block_annotation(
                        pending_block,
                        annotation_name,
                        payload,
                        line_number,
                        errors,
                    )
                    continue

                errors.append(
                    GraceParseIssue(
                        code=parser_module.ParseErrorCode.UNKNOWN_GRACE_ANNOTATION,
                        message=f"unknown GRACE annotation @grace.{annotation_name}",
                        line=line_number,
                    )
                )
                continue

            if not stripped:
                continue

            if pending_block is not None:
                if _is_comment_like_line(raw_line):
                    continue

                target = definition_targets.get(line_number)
                if target is not None:
                    block = parser_module._build_block_model(pending_block, target, line_number, errors)
                    pending_block = None
                    if block is None:
                        continue

                    if block.anchor_id in seen_anchor_ids:
                        errors.append(
                            GraceParseIssue(
                                code=parser_module.ParseErrorCode.DUPLICATE_ANCHOR_ID,
                                message=f"duplicate anchor id {block.anchor_id!r}",
                                line=line_number,
                            )
                        )
                        continue

                    seen_anchor_ids.add(block.anchor_id)
                    blocks.append(block)
                    continue

                errors.append(
                    GraceParseIssue(
                        code=parser_module.ParseErrorCode.ARBITRARY_CODE_BETWEEN_ANNOTATIONS_AND_BLOCK,
                        message="arbitrary code is not allowed between block annotations and the bound Go entity",
                        line=line_number,
                    )
                )
                pending_block = None
                continue

        if pending_block is not None:
            errors.append(
                GraceParseIssue(
                    code=parser_module.ParseErrorCode.ORPHAN_BLOCK_ANNOTATIONS,
                    message=(
                        f"block annotations for anchor {pending_block.anchor_id!r} "
                        "do not bind to a supported Go entity"
                    ),
                    line=pending_block.anchor_line,
                )
            )

        parser_module._finalize_module_annotations(module, errors)
        if errors:
            raise parser_module.GraceParseError(source_path, errors)

        parsed_file = {
            "module": module,
            "blocks": tuple(blocks),
        }
        return GraceFileModel(
            path=source_path,
            module=self.extract_module_metadata(parsed_file),
            blocks=self.extract_blocks(parsed_file),
        )


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
