# @grace.module grace.treesitter_base
# @grace.purpose Provide a shared Tree-sitter-backed GRACE adapter engine so new languages can be described mostly through declarative block queries and comment-host policies instead of bespoke parser loops.
# @grace.interfaces TreeSitterLanguageSpec(...); TreeSitterAdapterBase.build_grace_file_model(file_path:str|Path)->GraceFileModel
# @grace.invariant Tree-sitter language specs must emit the same GraceFileModel contract used by the rest of GRACE Core.
# @grace.invariant Tree-sitter matching remains deterministic by preserving query order and first-match line ownership.

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from tree_sitter import Language, Query, QueryCursor

from grace.language_adapter import GraceLanguageAdapter
from grace.models import BlockKind, GraceBlockMetadata, GraceFileModel, GraceModuleMetadata
from grace.tree_sitter_adapter import TreeSitterSourceFile, load_tree_sitter_source


_ANNOTATION_NAME_RE = r"(?P<name>[a-z_]+)"


@dataclass(frozen=True, slots=True)
class TreeSitterBlockQuerySpec:
    query: str
    kind: BlockKind
    symbol_capture: str
    block_capture: str = "block"
    owner_capture: str | None = None
    async_capture: str | None = None
    line_start_capture: str | None = None
    qualified_name_template: str | None = None
    promote_async_kind: BlockKind | None = None


# @grace.anchor grace.treesitter_base.TreeSitterLanguageSpec
# @grace.complexity 4
@dataclass(frozen=True, slots=True)
class TreeSitterLanguageSpec:
    language_name: str
    file_extensions: tuple[str, ...]
    language_factory: Callable[[], object]
    line_comment_prefixes: tuple[str, ...]
    block_query_specs: tuple[TreeSitterBlockQuerySpec, ...]
    block_comment_delimiters: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class _QueryTarget:
    kind: BlockKind
    symbol_name: str
    qualified_name: str
    is_async: bool
    line_start: int
    line_end: int


# @grace.anchor grace.treesitter_base.TreeSitterAdapterBase
# @grace.complexity 8
# @grace.belief Tree-sitter-backed adapters should share one deterministic engine for parsing and bootstrap discovery so the same AST queries define both semantic block binding and scaffold generation.
# @grace.links grace.language_adapter.GraceLanguageAdapter
class TreeSitterAdapterBase(GraceLanguageAdapter):
    spec: TreeSitterLanguageSpec

    def __init__(self, spec: TreeSitterLanguageSpec) -> None:
        self.spec = spec
        self.language_name = spec.language_name
        self.file_extensions = spec.file_extensions
        self.annotation_comment_prefix = spec.line_comment_prefixes[0] if spec.line_comment_prefixes else "#"

    def discover_annotations(self, source_text: str) -> tuple[str, ...]:
        discovered: list[str] = []
        for raw_line in source_text.splitlines():
            matched = _match_annotation_line(raw_line, self.spec)
            if matched is not None:
                discovered.append(matched[0])
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
                if _is_comment_like_line(raw_line, self.spec):
                    matched = _match_annotation_line(raw_line, self.spec)
                    if matched is not None and matched[0] in {"anchor", "complexity", "belief", "links"}:
                        saw_block_annotation = True
                    index -= 1
                    continue
                break
            return saw_block_annotation

        parsed_source = load_tree_sitter_source(file_path, self.spec.language_factory)
        definition_targets = _collect_definition_targets(parsed_source, self.spec)
        lines = parsed_source.source_text.splitlines()
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

        parsed_source = load_tree_sitter_source(file_path, self.spec.language_factory)
        definition_targets = _collect_definition_targets(parsed_source, self.spec)
        lines = parsed_source.source_text.splitlines()
        errors: list[object] = []
        module = parser_module._ModuleAccumulator()
        blocks: list[GraceBlockMetadata] = []
        pending_block: parser_module._PendingBlock | None = None
        block_section_started = False
        seen_anchor_ids: set[str] = set()

        for line_number, raw_line in enumerate(lines, start=1):
            matched_annotation = _match_annotation_line(raw_line, self.spec)
            stripped = raw_line.strip()

            if matched_annotation is not None:
                annotation_name, payload = matched_annotation
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
                if _is_comment_like_line(raw_line, self.spec):
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
                        message=(
                            "arbitrary code is not allowed between block annotations "
                            f"and the bound {self.spec.language_name} entity"
                        ),
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
                        f"do not bind to a supported {self.spec.language_name} entity"
                    ),
                    line=pending_block.anchor_line,
                )
            )

        parser_module._finalize_module_annotations(module, errors)
        if errors:
            raise parser_module.GraceParseError(parsed_source.path, errors)

        parsed_file = {
            "module": module,
            "blocks": tuple(blocks),
        }
        return GraceFileModel(
            path=parsed_source.path,
            module=self.extract_module_metadata(parsed_file),
            blocks=self.extract_blocks(parsed_file),
        )


def _compile_query(language_factory: Callable[[], object], query_text: str) -> Query:
    return Query(Language(language_factory()), query_text)


def _collect_definition_targets(
    parsed_source: TreeSitterSourceFile,
    spec: TreeSitterLanguageSpec,
) -> dict[int, object]:
    from grace import parser as parser_module

    targets: dict[int, object] = {}
    for query_spec in spec.block_query_specs:
        query = _compile_query(spec.language_factory, query_spec.query)
        cursor = QueryCursor(query)
        for _, captures in cursor.matches(parsed_source.tree.root_node):
            block_node = _first_capture(captures, query_spec.block_capture)
            symbol_node = _first_capture(captures, query_spec.symbol_capture)
            if block_node is None or symbol_node is None:
                continue

            owner_node = _first_capture(captures, query_spec.owner_capture) if query_spec.owner_capture else None
            symbol_name = _node_text(parsed_source.source_bytes, symbol_node)
            owner_name = _node_text(parsed_source.source_bytes, owner_node) if owner_node is not None else None
            is_async = any(getattr(child, "type", None) == "async" for child in getattr(block_node, "children", ()))
            kind = query_spec.promote_async_kind if is_async and query_spec.promote_async_kind is not None else query_spec.kind
            line_start_node = _first_capture(captures, query_spec.line_start_capture) if query_spec.line_start_capture else block_node
            qualified_name = _build_qualified_name(query_spec, symbol_name, owner_name)

            target = parser_module._DefinitionTarget(
                kind=kind,
                symbol_name=symbol_name,
                qualified_name=qualified_name,
                is_async=is_async,
                line_start=line_start_node.start_point.row + 1,
                line_end=block_node.end_point.row + 1,
            )
            targets.setdefault(target.line_start, target)
    return targets


def _first_capture(captures: dict[str, list[object]], capture_name: str | None) -> object | None:
    if capture_name is None:
        return None
    nodes = captures.get(capture_name)
    if not nodes:
        return None
    return nodes[0]


def _build_qualified_name(
    query_spec: TreeSitterBlockQuerySpec,
    symbol_name: str,
    owner_name: str | None,
) -> str:
    if query_spec.qualified_name_template is not None:
        return query_spec.qualified_name_template.format(
            symbol_name=symbol_name,
            owner_name=owner_name or "",
        )
    if owner_name:
        return f"{owner_name}.{symbol_name}"
    return symbol_name


def _match_annotation_line(raw_line: str, spec: TreeSitterLanguageSpec) -> tuple[str, str | None] | None:
    stripped = raw_line.strip()

    for prefix in spec.line_comment_prefixes:
        pattern = re.compile(
            rf"^\s*{re.escape(prefix)}\s*@grace\.{_ANNOTATION_NAME_RE}(?:\s+(?P<payload>.*\S))?\s*$"
        )
        match = pattern.match(raw_line)
        if match is not None:
            return match.group("name"), match.group("payload")

    for start, end in spec.block_comment_delimiters:
        pattern = re.compile(
            rf"^\s*{re.escape(start)}\s*@grace\.{_ANNOTATION_NAME_RE}(?:\s+(?P<payload>.*\S))?\s*{re.escape(end)}\s*$"
        )
        match = pattern.match(raw_line)
        if match is not None:
            return match.group("name"), match.group("payload")

    if stripped.startswith("@grace.") and "#" in spec.line_comment_prefixes:
        # Keep Python authoring backwards-compatible with files that already stripped comment prefixes.
        match = re.match(rf"^@grace\.{_ANNOTATION_NAME_RE}(?:\s+(?P<payload>.*\S))?\s*$", stripped)
        if match is not None:
            return match.group("name"), match.group("payload")

    return None


def _is_comment_like_line(raw_line: str, spec: TreeSitterLanguageSpec) -> bool:
    stripped = raw_line.lstrip()
    if any(stripped.startswith(prefix) for prefix in spec.line_comment_prefixes):
        return True
    return any(stripped.startswith(start) for start, _ in spec.block_comment_delimiters)


def _node_text(source_bytes: bytes, node: object | None) -> str:
    if node is None:
        return ""
    start_byte = getattr(node, "start_byte")
    end_byte = getattr(node, "end_byte")
    return source_bytes[start_byte:end_byte].decode("utf-8")


__all__ = [
    "TreeSitterAdapterBase",
    "TreeSitterBlockQuerySpec",
    "TreeSitterLanguageSpec",
]
