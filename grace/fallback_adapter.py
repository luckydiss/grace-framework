# @grace.module grace.fallback_adapter
# @grace.purpose Provide a deterministic text fallback for files without a dedicated runtime adapter so GRACE can still bootstrap basic anchor-driven workflows without inventing new source-of-truth semantics.
# @grace.interfaces FallbackTextAdapter.build_grace_file_model(file_path:str|Path)->GraceFileModel
# @grace.invariant The fallback adapter never changes inline annotations; it only uses text scanning to bind annotations to coarse block spans.
# @grace.invariant The fallback adapter favors safe, deterministic function-or-class style spans over language-specific inference.

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from grace.language_adapter import GraceLanguageAdapter
from grace.models import BlockKind, GraceBlockMetadata, GraceFileModel, GraceModuleMetadata

_LINE_COMMENT_PREFIXES = ("#", "//", "--", ";", "!")
_ANNOTATION_RE = re.compile(
    r"^\s*(?:#|//|--|;|!)\s*@grace\.(?P<name>[a-z_]+)(?:\s+(?P<payload>.*\S))?\s*$"
)
_BLOCK_START_PATTERNS = (
    (re.compile(r"^\s*(?:async\s+def|def|function|async\s+function)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\b"), BlockKind.FUNCTION, False),
    (re.compile(r"^\s*func\s*(?:\([^)]*\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("), BlockKind.FUNCTION, False),
    (re.compile(r"^\s*class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\b"), BlockKind.CLASS, False),
    (re.compile(r"^\s*type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+struct\b"), BlockKind.CLASS, False),
    (re.compile(r"^\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{"), BlockKind.FUNCTION, False),
)


# @grace.anchor grace.fallback_adapter.FallbackTextAdapter
# @grace.complexity 7
# @grace.belief Fallback bootstrap must stay conservative and text-only, so it exposes only coarse block discovery while leaving parsing and validation deterministic.
# @grace.links grace.language_adapter.GraceLanguageAdapter
class FallbackTextAdapter(GraceLanguageAdapter):
    language_name = "fallback"
    file_extensions: tuple[str, ...] = ()
    annotation_comment_prefix = "#"

    def discover_annotations(self, source_text: str) -> tuple[str, ...]:
        discovered: list[str] = []
        for raw_line in source_text.splitlines():
            match = _ANNOTATION_RE.match(raw_line)
            if match is not None:
                discovered.append(match.group("name"))
        return tuple(discovered)

    def extract_module_metadata(self, parsed_file: Any) -> GraceModuleMetadata:
        from grace.models import GraceModuleMetadata

        module = parsed_file["module"]
        return GraceModuleMetadata(
            module_id=module.module_id or "",
            purpose=module.purpose or "",
            interfaces=module.interfaces or "",
            invariants=tuple(module.invariants),
        )

    def extract_blocks(self, parsed_file: Any) -> tuple[GraceBlockMetadata, ...]:
        from grace.models import GraceBlockMetadata

        normalized_blocks: list[GraceBlockMetadata] = []
        for block in parsed_file["blocks"]:
            if isinstance(block, GraceBlockMetadata):
                normalized_blocks.append(block)
                continue

            if hasattr(block, "model_dump"):
                normalized_blocks.append(
                    GraceBlockMetadata.model_validate(block.model_dump(mode="python"))
                )
                continue

            normalized_blocks.append(GraceBlockMetadata.model_validate(block))
        return tuple(normalized_blocks)

    def compute_block_span(self, block: GraceBlockMetadata) -> tuple[int, int]:
        return (block.line_start, block.line_end)

    def discover_unannotated_blocks(self, file_path: str | Path) -> tuple[object, ...]:
        from grace.bootstrapper import BootstrapDiscoveredBlock

        def has_bound_block_annotations(lines: list[str], line_start: int) -> bool:
            saw_block_annotation = False
            index = line_start - 2
            while index >= 0:
                raw_line = lines[index]
                stripped = raw_line.strip()
                if not stripped:
                    index -= 1
                    continue
                if any(stripped.startswith(prefix) for prefix in _LINE_COMMENT_PREFIXES):
                    match = _ANNOTATION_RE.match(raw_line)
                    if match is not None and match.group("name") in {"anchor", "complexity", "belief", "links"}:
                        saw_block_annotation = True
                    index -= 1
                    continue
                break
            return saw_block_annotation

        source_path = Path(file_path)
        lines = source_path.read_text(encoding="utf-8").splitlines()
        definition_targets = _collect_definition_targets(lines)
        discovered_blocks: list[BootstrapDiscoveredBlock] = []

        for line_start, target in sorted(definition_targets.items()):
            if has_bound_block_annotations(lines, line_start):
                continue
            indent = ""
            if 0 < line_start <= len(lines):
                indent = lines[line_start - 1][: len(lines[line_start - 1]) - len(lines[line_start - 1].lstrip())]
            discovered_blocks.append(
                BootstrapDiscoveredBlock(
                    kind=target.kind,
                    symbol_name=target.symbol_name,
                    qualified_name=target.qualified_name,
                    line_start=target.line_start,
                    line_end=target.line_end,
                    indent=indent,
                )
            )

        return tuple(discovered_blocks)

    def build_grace_file_model(self, file_path: str | Path) -> GraceFileModel:
        from grace import parser as parser_module
        from grace.models import GraceFileModel

        source_path = Path(file_path)
        source_text = source_path.read_text(encoding="utf-8")
        lines = source_text.splitlines()
        definition_targets = _collect_definition_targets(lines)
        errors: list[object] = []
        module = parser_module._ModuleAccumulator()
        blocks: list[GraceBlockMetadata] = []
        pending_block: parser_module._PendingBlock | None = None
        block_section_started = False
        seen_anchor_ids: set[str] = set()

        for line_number, raw_line in enumerate(lines, start=1):
            match = _ANNOTATION_RE.match(raw_line)
            stripped = raw_line.strip()

            if match is not None:
                annotation_name = match.group("name")
                payload = match.group("payload")
                if annotation_name in parser_module.MODULE_ANNOTATIONS:
                    if block_section_started:
                        errors.append(
                            parser_module.GraceParseIssue(
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
                    parser_module.GraceParseIssue(
                        code=parser_module.ParseErrorCode.UNKNOWN_GRACE_ANNOTATION,
                        message=f"unknown GRACE annotation @grace.{annotation_name}",
                        line=line_number,
                    )
                )
                continue

            if not stripped:
                continue

            if pending_block is not None:
                if any(stripped.startswith(prefix) for prefix in _LINE_COMMENT_PREFIXES):
                    continue

                target = definition_targets.get(line_number)
                if target is not None:
                    block = parser_module._build_block_model(pending_block, target, line_number, errors)
                    pending_block = None
                    if block is None:
                        continue
                    if block.anchor_id in seen_anchor_ids:
                        errors.append(
                            parser_module.GraceParseIssue(
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
                    parser_module.GraceParseIssue(
                        code=parser_module.ParseErrorCode.ARBITRARY_CODE_BETWEEN_ANNOTATIONS_AND_BLOCK,
                        message="arbitrary code is not allowed between block annotations and the bound fallback entity",
                        line=line_number,
                    )
                )
                pending_block = None
                continue

        if pending_block is not None:
            errors.append(
                parser_module.GraceParseIssue(
                    code=parser_module.ParseErrorCode.ORPHAN_BLOCK_ANNOTATIONS,
                    message=(
                        f"block annotations for anchor {pending_block.anchor_id!r} "
                        "do not bind to a supported fallback entity"
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


def _collect_definition_targets(lines: list[str]) -> dict[int, object]:
    from grace import parser as parser_module

    targets: dict[int, object] = {}
    for index, raw_line in enumerate(lines):
        line_number = index + 1
        for pattern, kind, _ in _BLOCK_START_PATTERNS:
            match = pattern.match(raw_line)
            if match is None:
                continue

            symbol_name = match.group("name")
            qualified_name = symbol_name
            line_end = _compute_block_end(lines, index)
            targets.setdefault(
                line_number,
                parser_module._DefinitionTarget(
                    kind=kind,
                    symbol_name=symbol_name,
                    qualified_name=qualified_name,
                    is_async=False,
                    line_start=line_number,
                    line_end=line_end,
                ),
            )
            break
    return targets


def _compute_block_end(lines: list[str], start_index: int) -> int:
    brace_depth = 0
    seen_open_brace = False
    base_indent = len(lines[start_index]) - len(lines[start_index].lstrip())

    for index in range(start_index, len(lines)):
        line = lines[index]
        stripped = line.strip()

        brace_depth += line.count("{")
        if "{" in line:
            seen_open_brace = True
        brace_depth -= line.count("}")
        if seen_open_brace and brace_depth <= 0:
            return index + 1

        if index == start_index:
            continue

        if not stripped:
            continue

        current_indent = len(line) - len(line.lstrip())
        if current_indent <= base_indent and not any(stripped.startswith(prefix) for prefix in _LINE_COMMENT_PREFIXES):
            return index

    return len(lines)


__all__ = ["FallbackTextAdapter"]
