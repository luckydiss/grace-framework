from __future__ import annotations

from pathlib import Path

from grace.linter import LintIssueCode, lint_file
from grace.models import BlockKind, GraceBlockMetadata, GraceFileModel, GraceModuleMetadata


def test_lint_file_warns_on_todo_placeholders() -> None:
    grace_file = GraceFileModel(
        path=Path("module.py"),
        module=GraceModuleMetadata(
            module_id="demo.module",
            purpose="TODO",
            interfaces="TODO",
            invariants=("TODO",),
        ),
        blocks=(
            GraceBlockMetadata(
                anchor_id="demo.module.run",
                kind=BlockKind.FUNCTION,
                symbol_name="run",
                qualified_name="run",
                is_async=False,
                complexity=1,
                belief=None,
                links=(),
                line_start=1,
                line_end=2,
            ),
        ),
    )

    result = lint_file(grace_file)
    assert result.ok is False
    codes = {issue.code for issue in result.issues}
    assert LintIssueCode.TODO_PLACEHOLDER in codes
