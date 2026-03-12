from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from grace.models import (
    BlockKind,
    GraceBlockMetadata,
    GraceFileModel,
    GraceModuleMetadata,
    GraceParseFailure,
    GraceParseIssue,
    GraceParseResult,
    GraceParseSuccess,
    ParseErrorCode,
)

ANNOTATION_RE = re.compile(r"^\s*#\s*@grace\.(?P<name>[a-z_]+)(?:\s+(?P<payload>.*\S))?\s*$")
DECORATOR_RE = re.compile(r"^\s*@")
DEFINITION_RE = re.compile(r"^\s*(?:async\s+def|def|class)\b")

MODULE_ANNOTATIONS = {"module", "purpose", "interfaces", "invariant"}
BLOCK_ANNOTATIONS = {"anchor", "complexity", "belief", "links"}


class GraceParseError(ValueError):
    def __init__(self, path: Path, errors: list[GraceParseIssue]) -> None:
        self.path = path
        self.errors = tuple(errors)
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        summary = f"{self.path} failed GRACE parsing with {len(self.errors)} error(s)"
        details = "; ".join(
            f"{issue.code.value}@{issue.line}: {issue.message}" if issue.line else f"{issue.code.value}: {issue.message}"
            for issue in self.errors
        )
        return f"{summary}: {details}"


@dataclass(slots=True)
class _DefinitionTarget:
    kind: BlockKind
    symbol_name: str
    qualified_name: str
    is_async: bool
    line_start: int
    line_end: int


@dataclass(slots=True)
class _PendingBlock:
    anchor_id: str
    anchor_line: int
    complexity: int | None = None
    belief: str | None = None
    links: tuple[str, ...] = ()
    seen_annotations: set[str] = field(default_factory=lambda: {"anchor"})


@dataclass(slots=True)
class _ModuleAccumulator:
    module_id: str | None = None
    purpose: str | None = None
    interfaces: str | None = None
    invariants: list[str] = field(default_factory=list)


def parse_python_file(path: str | Path) -> GraceFileModel:
    source_path = Path(path)
    source_text = source_path.read_text(encoding="utf-8")
    lines = source_text.splitlines()
    errors: list[GraceParseIssue] = []

    try:
        tree = ast.parse(source_text, filename=str(source_path))
    except SyntaxError as exc:
        raise GraceParseError(
            source_path,
            [
                GraceParseIssue(
                    code=ParseErrorCode.PYTHON_SYNTAX_ERROR,
                    message=exc.msg,
                    line=exc.lineno,
                )
            ],
        ) from exc

    definition_targets = _collect_definition_targets(tree)
    module = _ModuleAccumulator()
    blocks: list[GraceBlockMetadata] = []
    pending_block: _PendingBlock | None = None
    block_section_started = False
    seen_anchor_ids: set[str] = set()

    for line_number, raw_line in enumerate(lines, start=1):
        match = ANNOTATION_RE.match(raw_line)
        stripped = raw_line.strip()

        if match:
            annotation_name = match.group("name")
            payload = (match.group("payload") or "").strip()

            if annotation_name in MODULE_ANNOTATIONS:
                if block_section_started:
                    errors.append(
                        GraceParseIssue(
                            code=ParseErrorCode.MODULE_ANNOTATION_AFTER_BLOCKS,
                            message=f"@grace.{annotation_name} is not allowed after block declarations start",
                            line=line_number,
                        )
                    )
                    continue
                _consume_module_annotation(module, annotation_name, payload, line_number, errors)
                continue

            if annotation_name in BLOCK_ANNOTATIONS:
                block_section_started = True
                pending_block = _consume_block_annotation(pending_block, annotation_name, payload, line_number, errors)
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

            if DECORATOR_RE.match(raw_line):
                continue

            if DEFINITION_RE.match(raw_line):
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

                block = _build_block_model(pending_block, target, line_number, errors)
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
                message=f"block annotations for anchor {pending_block.anchor_id!r} do not bind to a class/def/async def",
                line=pending_block.anchor_line,
            )
        )

    _finalize_module_annotations(module, errors)
    if errors:
        raise GraceParseError(source_path, errors)

    return GraceFileModel(
        path=source_path,
        module=GraceModuleMetadata(
            module_id=module.module_id or "",
            purpose=module.purpose or "",
            interfaces=module.interfaces or "",
            invariants=tuple(module.invariants),
        ),
        blocks=tuple(blocks),
    )


def try_parse_python_file(path: str | Path) -> GraceParseResult:
    source_path = Path(path)
    try:
        parsed_file = parse_python_file(source_path)
    except GraceParseError as exc:
        return GraceParseFailure(path=source_path, errors=exc.errors)
    return GraceParseSuccess(file=parsed_file)


def parse_python_module(path: str | Path) -> GraceFileModel:
    return parse_python_file(path)


def _consume_module_annotation(
    module: _ModuleAccumulator,
    annotation_name: str,
    payload: str,
    line_number: int,
    errors: list[GraceParseIssue],
) -> None:
    if not payload:
        errors.append(
            GraceParseIssue(
                code=ParseErrorCode.EMPTY_ANNOTATION_PAYLOAD,
                message=f"@grace.{annotation_name} requires non-empty text",
                line=line_number,
            )
        )
        return

    if annotation_name == "module":
        if module.module_id is not None:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.DUPLICATE_MODULE_ANNOTATION,
                    message="@grace.module must appear exactly once per file",
                    line=line_number,
                )
            )
            return
        if module.purpose is not None or module.interfaces is not None or module.invariants:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.MODULE_ANNOTATION_OUT_OF_ORDER,
                    message="@grace.module must be the first module-level annotation",
                    line=line_number,
                )
            )
            return
        module.module_id = payload
        return

    if annotation_name == "purpose":
        if module.purpose is not None:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.DUPLICATE_MODULE_ANNOTATION,
                    message="@grace.purpose must appear exactly once per file",
                    line=line_number,
                )
            )
            return
        if module.module_id is None or module.interfaces is not None or module.invariants:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.MODULE_ANNOTATION_OUT_OF_ORDER,
                    message="@grace.purpose must appear after @grace.module and before @grace.interfaces",
                    line=line_number,
                )
            )
            return
        module.purpose = payload
        return

    if annotation_name == "interfaces":
        if module.interfaces is not None:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.DUPLICATE_MODULE_ANNOTATION,
                    message="@grace.interfaces must appear exactly once per file",
                    line=line_number,
                )
            )
            return
        if module.module_id is None or module.purpose is None or module.invariants:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.MODULE_ANNOTATION_OUT_OF_ORDER,
                    message="@grace.interfaces must appear after @grace.purpose and before @grace.invariant",
                    line=line_number,
                )
            )
            return
        module.interfaces = payload
        return

    if annotation_name == "invariant":
        if module.module_id is None or module.purpose is None or module.interfaces is None:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.MODULE_ANNOTATION_OUT_OF_ORDER,
                    message="@grace.invariant must appear after @grace.interfaces",
                    line=line_number,
                )
            )
            return
        module.invariants.append(payload)


def _consume_block_annotation(
    pending: _PendingBlock | None,
    annotation_name: str,
    payload: str,
    line_number: int,
    errors: list[GraceParseIssue],
) -> _PendingBlock | None:
    if annotation_name == "anchor":
        if not payload:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.EMPTY_ANNOTATION_PAYLOAD,
                    message="@grace.anchor requires a non-empty anchor id",
                    line=line_number,
                )
            )
            return None
        if pending is not None:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.ORPHAN_BLOCK_ANNOTATIONS,
                    message=f"previous block annotations for anchor {pending.anchor_id!r} were not bound before a new @grace.anchor",
                    line=line_number,
                )
            )
        return _PendingBlock(anchor_id=payload, anchor_line=line_number)

    if pending is None:
        errors.append(
            GraceParseIssue(
                code=ParseErrorCode.BLOCK_ANNOTATION_WITHOUT_ANCHOR,
                message=f"@grace.{annotation_name} must appear after @grace.anchor",
                line=line_number,
            )
        )
        return None

    if annotation_name in pending.seen_annotations:
        errors.append(
            GraceParseIssue(
                code=ParseErrorCode.DUPLICATE_BLOCK_ANNOTATION,
                message=f"@grace.{annotation_name} must appear at most once per block",
                line=line_number,
            )
        )
        return pending

    if annotation_name == "complexity":
        if pending.complexity is not None or pending.belief is not None or pending.links:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.INVALID_BLOCK_ANNOTATION_ORDER,
                    message="@grace.complexity must appear immediately after @grace.anchor",
                    line=line_number,
                )
            )
            return pending
        try:
            complexity = int(payload)
        except ValueError:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.INVALID_COMPLEXITY,
                    message="@grace.complexity must be an integer from 1 to 10",
                    line=line_number,
                )
            )
            return pending
        if not 1 <= complexity <= 10:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.INVALID_COMPLEXITY,
                    message="@grace.complexity must be an integer from 1 to 10",
                    line=line_number,
                )
            )
            return pending
        pending.complexity = complexity
        pending.seen_annotations.add(annotation_name)
        return pending

    if annotation_name == "belief":
        if pending.complexity is None or pending.links:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.INVALID_BLOCK_ANNOTATION_ORDER,
                    message="@grace.belief must appear after @grace.complexity and before @grace.links",
                    line=line_number,
                )
            )
            return pending
        if not payload:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.EMPTY_ANNOTATION_PAYLOAD,
                    message="@grace.belief requires non-empty text",
                    line=line_number,
                )
            )
            return pending
        pending.belief = payload
        pending.seen_annotations.add(annotation_name)
        return pending

    if annotation_name == "links":
        if pending.complexity is None:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.INVALID_BLOCK_ANNOTATION_ORDER,
                    message="@grace.links must appear after @grace.complexity",
                    line=line_number,
                )
            )
            return pending
        links = tuple(item.strip() for item in payload.split(",") if item.strip())
        if not links:
            errors.append(
                GraceParseIssue(
                    code=ParseErrorCode.EMPTY_ANNOTATION_PAYLOAD,
                    message="@grace.links requires at least one anchor id",
                    line=line_number,
                )
            )
            return pending
        pending.links = links
        pending.seen_annotations.add(annotation_name)
        return pending

    return pending


def _build_block_model(
    pending: _PendingBlock,
    target: _DefinitionTarget,
    line_number: int,
    errors: list[GraceParseIssue],
) -> GraceBlockMetadata | None:
    if pending.complexity is None:
        errors.append(
            GraceParseIssue(
                code=ParseErrorCode.INVALID_BLOCK_ANNOTATION_ORDER,
                message="@grace.complexity is required for every GRACE block",
                line=pending.anchor_line,
            )
        )
        return None

    try:
        return GraceBlockMetadata(
            anchor_id=pending.anchor_id,
            kind=target.kind,
            symbol_name=target.symbol_name,
            qualified_name=target.qualified_name,
            is_async=target.is_async,
            complexity=pending.complexity,
            belief=pending.belief,
            links=pending.links,
            line_start=target.line_start,
            line_end=target.line_end,
        )
    except ValidationError as exc:
        for error in exc.errors():
            code = (
                ParseErrorCode.MISSING_REQUIRED_BELIEF
                if error["loc"] == ()
                else ParseErrorCode.INVALID_BINDING_TARGET
            )
            errors.append(
                GraceParseIssue(
                    code=code,
                    message=error["msg"],
                    line=line_number,
                )
            )
        return None


def _finalize_module_annotations(module: _ModuleAccumulator, errors: list[GraceParseIssue]) -> None:
    if module.module_id is None:
        errors.append(
            GraceParseIssue(
                code=ParseErrorCode.MISSING_REQUIRED_MODULE_ANNOTATION,
                message="missing required @grace.module",
            )
        )
    if module.purpose is None:
        errors.append(
            GraceParseIssue(
                code=ParseErrorCode.MISSING_REQUIRED_MODULE_ANNOTATION,
                message="missing required @grace.purpose",
            )
        )
    if module.interfaces is None:
        errors.append(
            GraceParseIssue(
                code=ParseErrorCode.MISSING_REQUIRED_MODULE_ANNOTATION,
                message="missing required @grace.interfaces",
            )
        )
    if not module.invariants:
        errors.append(
            GraceParseIssue(
                code=ParseErrorCode.MISSING_REQUIRED_MODULE_ANNOTATION,
                message="missing required @grace.invariant",
            )
        )


def _collect_definition_targets(tree: ast.AST) -> dict[int, _DefinitionTarget]:
    targets: dict[int, _DefinitionTarget] = {}
    _walk_statement_list(getattr(tree, "body", []), targets, scope=(), direct_class=None)
    return targets


def _walk_statement_list(
    statements: list[ast.stmt],
    targets: dict[int, _DefinitionTarget],
    scope: tuple[str, ...],
    direct_class: str | None,
) -> None:
    for statement in statements:
        if isinstance(statement, ast.ClassDef):
            qualified_name = ".".join((*scope, statement.name))
            targets[statement.lineno] = _DefinitionTarget(
                kind=BlockKind.CLASS,
                symbol_name=statement.name,
                qualified_name=qualified_name,
                is_async=False,
                line_start=statement.lineno,
                line_end=getattr(statement, "end_lineno", statement.lineno),
            )
            _walk_statement_list(statement.body, targets, scope=(*scope, statement.name), direct_class=statement.name)
            continue

        if isinstance(statement, ast.FunctionDef):
            qualified_name = ".".join((*scope, statement.name))
            targets[statement.lineno] = _DefinitionTarget(
                kind=BlockKind.METHOD if direct_class else BlockKind.FUNCTION,
                symbol_name=statement.name,
                qualified_name=qualified_name,
                is_async=False,
                line_start=statement.lineno,
                line_end=getattr(statement, "end_lineno", statement.lineno),
            )
            _walk_nested_bodies(statement, targets, scope=(*scope, statement.name))
            continue

        if isinstance(statement, ast.AsyncFunctionDef):
            qualified_name = ".".join((*scope, statement.name))
            targets[statement.lineno] = _DefinitionTarget(
                kind=BlockKind.METHOD if direct_class else BlockKind.ASYNC_FUNCTION,
                symbol_name=statement.name,
                qualified_name=qualified_name,
                is_async=True,
                line_start=statement.lineno,
                line_end=getattr(statement, "end_lineno", statement.lineno),
            )
            _walk_nested_bodies(statement, targets, scope=(*scope, statement.name))
            continue

        _walk_nested_bodies(statement, targets, scope=scope)


def _walk_nested_bodies(node: ast.AST, targets: dict[int, _DefinitionTarget], scope: tuple[str, ...]) -> None:
    for field_name in ("body", "orelse", "finalbody"):
        value = getattr(node, field_name, None)
        if isinstance(value, list) and value and all(isinstance(item, ast.stmt) for item in value):
            _walk_statement_list(value, targets, scope=scope, direct_class=None)

    handlers = getattr(node, "handlers", None)
    if isinstance(handlers, list):
        for handler in handlers:
            if isinstance(handler, ast.ExceptHandler):
                _walk_statement_list(handler.body, targets, scope=scope, direct_class=None)


__all__ = [
    "GraceParseError",
    "parse_python_file",
    "parse_python_module",
    "try_parse_python_file",
]
