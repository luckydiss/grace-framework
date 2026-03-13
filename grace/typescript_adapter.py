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
# @grace.complexity 5
class TypeScriptAdapter(GraceLanguageAdapter):
    language_name = "typescript"
    file_extensions = (".ts",)

    # @grace.anchor grace.typescript_adapter.TypeScriptAdapter.discover_annotations
    # @grace.complexity 2
    def discover_annotations(self, source_text: str) -> tuple[str, ...]:
        discovered: list[str] = []
        for raw_line in source_text.splitlines():
            match = _match_annotation_line(raw_line)
            if match is None:
                continue
            discovered.append(match[0])
        return tuple(discovered)

    # @grace.anchor grace.typescript_adapter.TypeScriptAdapter.extract_module_metadata
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

    # @grace.anchor grace.typescript_adapter.TypeScriptAdapter.extract_blocks
    # @grace.complexity 2
    def extract_blocks(self, parsed_file: Any) -> tuple[GraceBlockMetadata, ...]:
        return tuple(parsed_file["blocks"])

    # @grace.anchor grace.typescript_adapter.TypeScriptAdapter.compute_block_span
    # @grace.complexity 1
    def compute_block_span(self, block: GraceBlockMetadata) -> tuple[int, int]:
        return (block.line_start, block.line_end)

    # @grace.anchor grace.typescript_adapter.TypeScriptAdapter.build_grace_file_model
    # @grace.complexity 7
    # @grace.belief The pilot adapter should reuse the existing GRACE module and block annotation state machine for parity, while Tree-sitter supplies only TypeScript entity detection and deterministic spans.
    # @grace.links grace.typescript_adapter._collect_definition_targets
    def build_grace_file_model(self, file_path: str | Path):
        from grace import parser as parser_module
        from grace.models import GraceFileModel

        parsed_source = load_tree_sitter_source(file_path, language_typescript)
        definition_targets = _collect_definition_targets(parsed_source)
        lines = parsed_source.source_text.splitlines()
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
                        message="arbitrary code is not allowed between block annotations and the bound TypeScript entity",
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
                        "do not bind to a supported TypeScript entity"
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


# @grace.anchor grace.typescript_adapter._collect_definition_targets
# @grace.complexity 5
# @grace.links grace.tree_sitter_adapter.iter_tree_nodes
def _collect_definition_targets(parsed_source: TreeSitterSourceFile) -> dict[int, object]:
    from grace import parser as parser_module

    targets: dict[int, object] = {}
    for node in iter_tree_nodes(parsed_source.tree.root_node):
        if node.type == "function_declaration":
            target = _build_function_target(parsed_source.source_bytes, node)
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
