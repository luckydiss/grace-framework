# @grace.module grace.parser
# @grace.purpose Parse inline GRACE annotations from Python source into typed file models.
# @grace.interfaces parse_python_file(path)->GraceFileModel; try_parse_python_file(path)->GraceParseResult; parse_python_module(path)->GraceFileModel
# @grace.invariant Inline annotations remain the only parsing source of truth; parser never consults sidecars or exports.
# @grace.invariant Block annotations bind only to the nearest next class, def, or async def accepted by the grammar.
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


# @grace.anchor grace.parser.GraceParseError
# @grace.complexity 2
class GraceParseError(ValueError):
    # @grace.anchor grace.parser.GraceParseError.__init__
    # @grace.complexity 1
    def __init__(self, path: Path, errors: list[GraceParseIssue]) -> None:
        self.path = path
        self.errors = tuple(errors)
        super().__init__(self._build_message())

    # @grace.anchor grace.parser.GraceParseError._build_message
    # @grace.complexity 2
    def _build_message(self) -> str:
        summary = f"{self.path} failed GRACE parsing with {len(self.errors)} error(s)"
        details = "; ".join(
            f"{issue.code.value}@{issue.line}: {issue.message}" if issue.line else f"{issue.code.value}: {issue.message}"
            for issue in self.errors
        )
        return f"{summary}: {details}"


# @grace.anchor grace.parser._DefinitionTarget
# @grace.complexity 1
@dataclass(slots=True)
class _DefinitionTarget:
    kind: BlockKind
    symbol_name: str
    qualified_name: str
    is_async: bool
    line_start: int
    line_end: int


# @grace.anchor grace.parser._PendingBlock
# @grace.complexity 2
@dataclass(slots=True)
class _PendingBlock:
    anchor_id: str
    anchor_line: int
    complexity: int | None = None
    belief: str | None = None
    links: tuple[str, ...] = ()
    seen_annotations: set[str] = field(default_factory=lambda: {"anchor"})


# @grace.anchor grace.parser._ModuleAccumulator
# @grace.complexity 1
@dataclass(slots=True)
class _ModuleAccumulator:
    module_id: str | None = None
    purpose: str | None = None
    interfaces: str | None = None
    invariants: list[str] = field(default_factory=list)


# @grace.anchor grace.parser.parse_python_file
# @grace.complexity 7
# @grace.belief The parser entrypoint should stay language-agnostic while remaining self-contained under reload-heavy test and dogfood workflows, so it uses the paired adapter module when available and falls back to the registered language adapter lookup otherwise.
# @grace.links grace.language_adapter.get_language_adapter_for_path
def parse_python_file(path: str | Path) -> GraceFileModel:
    import sys

    source_path = Path(path)
    adapter_module = getattr(sys.modules[__name__], "_grace_language_adapter_module", None)
    if adapter_module is None:
        from grace.language_adapter import get_language_adapter_for_path
    else:
        get_language_adapter_for_path = adapter_module.get_language_adapter_for_path

    adapter = get_language_adapter_for_path(source_path)
    return adapter.build_grace_file_model(source_path)


# @grace.anchor grace.parser.try_parse_python_file
# @grace.complexity 2
# @grace.links grace.parser.parse_python_file
def try_parse_python_file(path: str | Path) -> GraceParseResult:
    source_path = Path(path)
    try:
        parsed_file = parse_python_file(source_path)
    except GraceParseError as exc:
        return GraceParseFailure(path=source_path, errors=exc.errors)
    return GraceParseSuccess(file=parsed_file)


# @grace.anchor grace.parser.parse_python_module
# @grace.complexity 1
# @grace.links grace.parser.parse_python_file
def parse_python_module(path: str | Path) -> GraceFileModel:
    return parse_python_file(path)


# @grace.anchor grace.parser._consume_module_annotation
# @grace.complexity 5
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


# @grace.anchor grace.parser._consume_block_annotation
# @grace.complexity 6
# @grace.belief Block-annotation parsing is a strict state machine: preserving order and single-occurrence constraints here is simpler and more deterministic than deferring malformed sequences to later validation passes.
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


# @grace.anchor grace.parser._build_block_model
# @grace.complexity 5
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


# @grace.anchor grace.parser._finalize_module_annotations
# @grace.complexity 2
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


# @grace.anchor grace.parser._collect_definition_targets
# @grace.complexity 3
# @grace.links grace.parser._walk_statement_list
def _collect_definition_targets(tree: ast.AST) -> dict[int, _DefinitionTarget]:
    targets: dict[int, _DefinitionTarget] = {}
    _walk_statement_list(getattr(tree, "body", []), targets, scope=(), direct_class=None)
    return targets


# @grace.anchor grace.parser._walk_statement_list
# @grace.complexity 6
# @grace.belief AST traversal must distinguish top-level functions from methods without inventing new semantic kinds; carrying scope and direct_class explicitly keeps method namespace derivation deterministic.
# @grace.links grace.parser._walk_nested_bodies
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


# @grace.anchor grace.parser._walk_nested_bodies
# @grace.complexity 4
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
