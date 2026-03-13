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
class PythonAdapter(GraceLanguageAdapter):
    language_name = "python"
    file_extensions = (".py",)

    # @grace.anchor grace.python_adapter.PythonAdapter.discover_annotations
    # @grace.complexity 2
    def discover_annotations(self, source_text: str) -> tuple[str, ...]:
        from grace import parser as parser_module

        discovered: list[str] = []
        for raw_line in source_text.splitlines():
            match = parser_module.ANNOTATION_RE.match(raw_line)
            if match:
                discovered.append(match.group("name"))
        return tuple(discovered)

    # @grace.anchor grace.python_adapter.PythonAdapter.extract_module_metadata
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

    # @grace.anchor grace.python_adapter.PythonAdapter.extract_blocks
    # @grace.complexity 2
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

    # @grace.anchor grace.python_adapter.PythonAdapter.compute_block_span
    # @grace.complexity 2
    def compute_block_span(self, block: GraceBlockMetadata) -> tuple[int, int]:
        return (block.line_start, block.line_end)

    # @grace.anchor grace.python_adapter.PythonAdapter.build_grace_file_model
    # @grace.complexity 7
    # @grace.belief The adapter should preserve the old Python parser behavior exactly: reuse the parser module's strict annotation state machine and AST traversal helpers, but route entry through the adapter contract so future languages can integrate without changing core consumers.
    def build_grace_file_model(self, file_path: str | Path):
        from grace import parser as parser_module
        from grace.models import GraceFileModel

        source_path = Path(file_path)
        source_text = source_path.read_text(encoding="utf-8")
        lines = source_text.splitlines()
        errors: list[GraceParseIssue] = []

        try:
            tree = ast.parse(source_text, filename=str(source_path))
        except SyntaxError as exc:
            raise parser_module.GraceParseError(
                source_path,
                [
                    GraceParseIssue(
                        code=ParseErrorCode.PYTHON_SYNTAX_ERROR,
                        message=exc.msg,
                        line=exc.lineno,
                    )
                ],
            ) from exc

        definition_targets = parser_module._collect_definition_targets(tree)
        module = parser_module._ModuleAccumulator()
        blocks: list[GraceBlockMetadata] = []
        pending_block: parser_module._PendingBlock | None = None
        block_section_started = False
        seen_anchor_ids: set[str] = set()

        for line_number, raw_line in enumerate(lines, start=1):
            match = parser_module.ANNOTATION_RE.match(raw_line)
            stripped = raw_line.strip()

            if match:
                annotation_name = match.group("name")
                payload = (match.group("payload") or "").strip()

                if annotation_name in parser_module.MODULE_ANNOTATIONS:
                    if block_section_started:
                        errors.append(
                            GraceParseIssue(
                                code=ParseErrorCode.MODULE_ANNOTATION_AFTER_BLOCKS,
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
                        code=ParseErrorCode.UNKNOWN_GRACE_ANNOTATION,
                        message=f"unknown GRACE annotation @grace.{annotation_name}",
                        line=line_number,
                    )
                )
                continue

            if not stripped:
                continue

            if pending_block is not None:
                if stripped.startswith("#"):
                    continue

                if parser_module.DECORATOR_RE.match(raw_line):
                    continue

                if parser_module.DEFINITION_RE.match(raw_line):
                    target = definition_targets.get(line_number)
                    if target is None:
                        errors.append(
                            GraceParseIssue(
                                code=ParseErrorCode.INVALID_BINDING_TARGET,
                                message="block annotations must bind to the nearest next class/def/async def",
                                line=line_number,
                            )
                        )
                        pending_block = None
                        continue

                    block = parser_module._build_block_model(pending_block, target, line_number, errors)
                    pending_block = None
                    if block is None:
                        continue

                    if block.anchor_id in seen_anchor_ids:
                        errors.append(
                            GraceParseIssue(
                                code=ParseErrorCode.DUPLICATE_ANCHOR_ID,
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
                        code=ParseErrorCode.ARBITRARY_CODE_BETWEEN_ANNOTATIONS_AND_BLOCK,
                        message="arbitrary code is not allowed between block annotations and the bound class/def/async def",
                        line=line_number,
                    )
                )
                pending_block = None
                continue

        if pending_block is not None:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.ORPHAN_BLOCK_ANNOTATIONS,
                    message=(
                        f"block annotations for anchor {pending_block.anchor_id!r} "
                        "do not bind to a class/def/async def"
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


from grace.language_adapter import _register_python_adapter

_register_python_adapter(PythonAdapter)


__all__ = ["PythonAdapter"]
