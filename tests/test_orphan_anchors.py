from __future__ import annotations

from pathlib import Path

from grace.linter import LintFailure, LintIssueCode, lint_project
from grace.models import BlockKind, GraceBlockMetadata, GraceFileModel, GraceModuleMetadata


def make_block(
    anchor_id: str,
    symbol_name: str,
    *,
    links: tuple[str, ...] = (),
    line_start: int = 1,
) -> GraceBlockMetadata:
    return GraceBlockMetadata(
        anchor_id=anchor_id,
        kind=BlockKind.FUNCTION,
        symbol_name=symbol_name,
        qualified_name=symbol_name,
        complexity=1,
        links=links,
        line_start=line_start,
        line_end=line_start + 2,
    )


def make_file(module_id: str, interfaces: str, blocks: tuple[GraceBlockMetadata, ...]) -> GraceFileModel:
    return GraceFileModel(
        path=Path(f"{module_id.replace('.', '_')}.py"),
        module=GraceModuleMetadata(
            module_id=module_id,
            purpose="Provide deterministic test coverage for orphan anchor linting.",
            interfaces=interfaces,
            invariants=("Anchors remain stable for lint tests.",),
        ),
        blocks=blocks,
    )


def test_lint_project_warns_for_non_public_anchor_without_incoming_links() -> None:
    grace_file = make_file(
        "demo.orphans",
        "entry()",
        (
            make_block("demo.orphans.entry", "entry", line_start=1),
            make_block("demo.orphans.orphaned_helper", "orphaned_helper", line_start=10),
        ),
    )

    result = lint_project([grace_file])

    assert isinstance(result, LintFailure)
    orphan_issues = [issue for issue in result.issues if issue.code is LintIssueCode.ORPHAN_ANCHOR]
    assert [issue.anchor_id for issue in orphan_issues] == ["demo.orphans.orphaned_helper"]


def test_lint_project_does_not_warn_for_public_or_incoming_anchors() -> None:
    grace_file = make_file(
        "demo.links",
        "entry()",
        (
            make_block("demo.links.entry", "entry", links=("demo.links.helper",), line_start=1),
            make_block("demo.links.helper", "helper", line_start=10),
        ),
    )

    result = lint_project([grace_file])

    if isinstance(result, LintFailure):
        orphan_issues = [issue for issue in result.issues if issue.code is LintIssueCode.ORPHAN_ANCHOR]
        assert orphan_issues == []


def test_lint_project_emits_orphan_warnings_in_deterministic_anchor_order() -> None:
    grace_file = make_file(
        "demo.ordering",
        "entry()",
        (
            make_block("demo.ordering.entry", "entry", line_start=1),
            make_block("demo.ordering.alpha", "alpha", line_start=10),
            make_block("demo.ordering.beta", "beta", line_start=20),
        ),
    )

    result = lint_project([grace_file])

    assert isinstance(result, LintFailure)
    orphan_issues = [issue for issue in result.issues if issue.code is LintIssueCode.ORPHAN_ANCHOR]
    assert [issue.anchor_id for issue in orphan_issues] == [
        "demo.ordering.alpha",
        "demo.ordering.beta",
    ]
