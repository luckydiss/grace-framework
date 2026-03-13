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


def test_v1_readiness_current_green_surfaces_match_review() -> None:
    parse_payload = invoke_json_expect_success("parse", ".", "--json")
    map_payload = invoke_json_expect_success("map", ".", "--json")
    validate_payload = invoke_json_expect_success("validate", "grace", "--json")
    lint_payload = invoke_json_expect_success("lint", "grace", "--json")

    assert parse_payload["ok"] is True
    assert parse_payload["scope"] == "project"
    assert map_payload["grace_version"] == "v1"
    assert validate_payload["validation"] == {"ok": True, "scope": "project"}
    assert lint_payload["ok"] is True


def test_v1_readiness_repo_root_validation_now_matches_configured_scope() -> None:
    validate_payload = invoke_json_expect_success("validate", ".", "--json")
    lint_payload = invoke_json_expect_success("lint", ".", "--json")

    assert validate_payload["ok"] is True
    assert validate_payload["scope"] == "project"
    assert validate_payload["validation"] == {"ok": True, "scope": "project"}

    assert lint_payload["ok"] is True
    assert lint_payload["scope"] == "project"
