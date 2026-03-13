from __future__ import annotations

import importlib.util
import shutil
import sys
import textwrap
import types
from functools import lru_cache
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_modules():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.language_adapter",
        "grace.python_adapter",
        "grace.linter",
        "grace.artifact_hygiene",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "linter", "artifact_hygiene"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["models"], loaded["parser"], loaded["linter"], loaded["artifact_hygiene"]


MODELS, PARSER, LINTER, HYGIENE = load_modules()


@pytest.fixture
def writable_repo(tmp_path: Path) -> Path:
    repo = tmp_path.parent / f"{tmp_path.name}_artifact_hygiene_repo"
    repo.mkdir(parents=True, exist_ok=True)
    try:
        repo.chmod(0o777)
    except OSError:
        pass
    (repo / ".gitignore").write_text("", encoding="utf-8")
    try:
        yield repo
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def make_grace_file() -> str:
    return (
        "# @grace.module billing.pricing\n"
        "# @grace.purpose Determine pricing behavior.\n"
        "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
        "# @grace.invariant Discount percent must never be negative.\n\n"
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 1\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return price - ((price * percent) // 100)\n"
    )


def test_discover_unignored_artifact_paths_respects_gitignore(writable_repo: Path) -> None:
    repo = writable_repo
    write_text(
        repo / ".gitignore",
        """
        .tmp_*.pyfrag
        .grace_plan_*
        """,
    )
    write_text(repo / ".tmp_patch.pyfrag", "temporary")
    write_text(repo / "manual.plan.json", "{}")
    write_text(repo / ".grace.tmp.json", "{}")
    (repo / ".grace_plan_deadbeef").mkdir(parents=True, exist_ok=True)

    unignored = HYGIENE.discover_unignored_artifact_paths(repo)

    assert unignored == (
        (repo / ".grace.tmp.json").resolve(),
        (repo / "manual.plan.json").resolve(),
    )


def test_clean_artifacts_removes_only_temp_patterns(writable_repo: Path) -> None:
    repo = writable_repo
    tmp_pyfrag = write_text(repo / ".tmp_patch.pyfrag", "temporary")
    tmp_json = write_text(repo / ".tmp_patch.json", "{}")
    grace_tmp_json = write_text(repo / ".grace.tmp.json", "{}")
    grace_plan_dir = repo / ".grace_plan_deadbeef"
    grace_plan_dir.mkdir(parents=True, exist_ok=True)
    write_text(grace_plan_dir / "nested.py", "print('x')")
    keep_plan = write_text(repo / "committed.plan.json", "{}")
    keep_pyfrag = write_text(repo / "committed.pyfrag", "replacement")

    dry_run = HYGIENE.clean_artifacts(repo, dry_run=True)
    assert dry_run.cleaned_paths == (
        grace_tmp_json.resolve(),
        grace_plan_dir.resolve(),
        tmp_json.resolve(),
        tmp_pyfrag.resolve(),
    )
    assert keep_plan.exists()
    assert keep_pyfrag.exists()
    assert grace_plan_dir.exists()

    result = HYGIENE.clean_artifacts(repo)
    assert result.failed_paths == ()
    assert result.cleaned_paths == dry_run.cleaned_paths
    assert not tmp_pyfrag.exists()
    assert not tmp_json.exists()
    assert not grace_tmp_json.exists()
    assert not grace_plan_dir.exists()
    assert keep_plan.exists()
    assert keep_pyfrag.exists()


def test_lint_project_reports_untracked_artifact_warning(writable_repo: Path) -> None:
    repo = writable_repo
    source_path = write_text(repo / "pricing.py", make_grace_file())
    write_text(repo / "manual.plan.json", "{}")

    parsed = PARSER.parse_python_file(source_path)
    result = LINTER.lint_project((parsed,))

    assert isinstance(result, LINTER.LintFailure)
    assert any(issue.code is LINTER.LintIssueCode.UNTRACKED_ARTIFACT for issue in result.issues)
