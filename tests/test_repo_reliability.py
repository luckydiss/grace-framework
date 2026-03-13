from __future__ import annotations

import importlib.util
import json
import sys
import types
from functools import lru_cache
from pathlib import Path

from click.testing import CliRunner
import pytest


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_cli_module():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.language_adapter",
        "grace.python_adapter",
        "grace.typescript_adapter",
        "grace.go_adapter",
        "grace.validator",
        "grace.linter",
        "grace.map",
        "grace.patcher",
        "grace.plan",
        "grace.query",
        "grace.impact",
        "grace.read",
        "grace.planner",
        "grace.cli",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in (
        "models",
        "parser",
        "validator",
        "linter",
        "map",
        "patcher",
        "plan",
        "query",
        "impact",
        "read",
        "planner",
        "cli",
    ):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["cli"]


CLI = load_cli_module()


@pytest.fixture(autouse=True)
def _reload_modules():
    global CLI
    load_cli_module.cache_clear()
    CLI = load_cli_module()


def runner() -> CliRunner:
    return CliRunner()


def invoke_json_expect_success(*args: str) -> dict:
    result = runner().invoke(CLI.app, list(args))
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def invoke_json(*args: str) -> tuple[int, dict]:
    result = runner().invoke(CLI.app, list(args))
    return result.exit_code, json.loads(result.output)


def build_reliability_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    eval_dir = tmp_path.parent / f"{tmp_path.name}_repo_reliability"
    eval_dir.mkdir(parents=True, exist_ok=True)

    replacement_path = eval_dir / "map.build_file_map.replacement.pyfrag"
    replacement_path.write_text(
        (
            "# @grace.anchor grace.map.build_file_map\n"
            "# @grace.complexity 1\n"
            "# @grace.links grace.map.build_project_map\n"
            "def build_file_map(grace_file: GraceFileModel) -> GraceMap:\n"
            "    single_file_project = (grace_file,)\n"
            "    return build_project_map(single_file_project)\n"
        ),
        encoding="utf-8",
    )

    plan_path = eval_dir / "repo_reliability.plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "grace_version": "v1",
                "entries": [
                    {
                        "path": str((ROOT / "grace" / "map.py").resolve()),
                        "anchor_id": "grace.map.build_file_map",
                        "operation": "replace_block",
                        "replacement_file": str(replacement_path.resolve()),
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return replacement_path, plan_path


def compute_repo_reliability_metrics(tmp_path: Path) -> dict[str, float]:
    deterministic_checks = 0
    deterministic_successes = 0

    parse_first = invoke_json_expect_success("parse", ".", "--json")
    parse_second = invoke_json_expect_success("parse", ".", "--json")
    deterministic_checks += 1
    deterministic_successes += int(parse_first == parse_second)

    map_first = invoke_json_expect_success("map", ".", "--json")
    map_second = invoke_json_expect_success("map", ".", "--json")
    deterministic_checks += 1
    deterministic_successes += int(map_first == map_second)

    query_first = invoke_json_expect_success("query", "anchors", "grace", "--json")
    query_second = invoke_json_expect_success("query", "anchors", "grace", "--json")
    deterministic_checks += 1
    deterministic_successes += int(query_first == query_second)

    read_first = invoke_json_expect_success("read", "grace", "grace.map.build_file_map", "--json")
    read_second = invoke_json_expect_success("read", "grace", "grace.map.build_file_map", "--json")
    deterministic_checks += 1
    deterministic_successes += int(read_first == read_second)

    impact_first = invoke_json_expect_success("impact", "grace", "grace.map.build_file_map", "--json")
    impact_second = invoke_json_expect_success("impact", "grace", "grace.map.build_file_map", "--json")
    deterministic_checks += 1
    deterministic_successes += int(impact_first == impact_second)

    plan_first = invoke_json_expect_success("plan", "impact", "grace", "grace.map.build_file_map", "--json")
    plan_second = invoke_json_expect_success("plan", "impact", "grace", "grace.map.build_file_map", "--json")
    deterministic_checks += 1
    deterministic_successes += int(plan_first == plan_second)

    curated_scopes = (
        "grace",
        str(ROOT / "examples" / "basic"),
        str(ROOT / "examples" / "go"),
        str(ROOT / "examples" / "typescript"),
        str(ROOT / "examples" / "parity" / "python"),
        str(ROOT / "examples" / "parity" / "typescript"),
        str(ROOT / "examples" / "parity" / "go"),
    )
    curated_successes = 0
    for scope in curated_scopes:
        exit_code, payload = invoke_json("validate", scope, "--json")
        curated_successes += int(exit_code == 0 and payload["ok"] is True)

    repo_root_export_successes = 0
    repo_root_export_successes += int(parse_first["ok"] is True)
    repo_root_export_successes += int(map_first["grace_version"] == "v1")

    replacement_path, plan_path = build_reliability_artifacts(tmp_path)
    patch_payload = invoke_json_expect_success(
        "patch",
        str(ROOT / "grace" / "map.py"),
        "grace.map.build_file_map",
        str(replacement_path),
        "--dry-run",
        "--json",
    )
    apply_plan_payload = invoke_json_expect_success(
        "apply-plan",
        str(plan_path),
        "--dry-run",
        "--preview",
        "--json",
    )

    touched_paths = {Path(entry["path"]).resolve() for entry in apply_plan_payload["entries"]}
    expected_paths = {(ROOT / "grace" / "map.py").resolve()}
    unnecessary_file_touches = len(touched_paths - expected_paths) + int(
        Path(patch_payload["path"]).resolve() != (ROOT / "grace" / "map.py").resolve()
    )
    touched_file_count = len(touched_paths) + 1

    return {
        "deterministic_cli_contract_rate": deterministic_successes / deterministic_checks,
        "curated_scope_validation_rate": curated_successes / len(curated_scopes),
        "repo_root_export_success_rate": repo_root_export_successes / 2,
        "dry_run_patch_plan_success_rate": (
            int(patch_payload["ok"] is True) + int(apply_plan_payload["ok"] is True)
        )
        / 2,
        "unnecessary_file_touch_rate": unnecessary_file_touches / touched_file_count if touched_file_count else 0.0,
    }


def test_repo_reliability_metrics_are_stable(tmp_path: Path) -> None:
    metrics = compute_repo_reliability_metrics(tmp_path)

    assert metrics == {
        "deterministic_cli_contract_rate": 1.0,
        "curated_scope_validation_rate": 1.0,
        "repo_root_export_success_rate": 1.0,
        "dry_run_patch_plan_success_rate": 1.0,
        "unnecessary_file_touch_rate": 0.0,
    }


def test_repo_root_and_curated_scope_policy_behave_as_documented() -> None:
    parse_payload = invoke_json_expect_success("parse", ".", "--json")
    map_payload = invoke_json_expect_success("map", ".", "--json")
    validate_exit_code, validate_payload = invoke_json("validate", ".", "--json")
    lint_exit_code, lint_payload = invoke_json("lint", ".", "--json")

    assert parse_payload["ok"] is True
    assert parse_payload["scope"] == "project"
    assert map_payload["grace_version"] == "v1"
    assert validate_exit_code != 0
    assert validate_payload["stage"] == "validate"
    assert any(issue["code"] == "duplicate_module_id" for issue in validate_payload["issues"])
    assert lint_exit_code != 0
    assert lint_payload["stage"] == "validate"

    for curated_scope in (
        "grace",
        str(ROOT / "examples" / "basic"),
        str(ROOT / "examples" / "go"),
        str(ROOT / "examples" / "typescript"),
        str(ROOT / "examples" / "parity" / "python"),
        str(ROOT / "examples" / "parity" / "typescript"),
        str(ROOT / "examples" / "parity" / "go"),
    ):
        payload = invoke_json_expect_success("validate", curated_scope, "--json")
        assert payload["ok"] is True
