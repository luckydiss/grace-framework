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
def load_cli_modules():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.language_adapter",
        "grace.python_adapter",
        "grace.go_adapter",
        "grace.tree_sitter_adapter",
        "grace.typescript_adapter",
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
        "language_adapter",
        "python_adapter",
        "go_adapter",
        "tree_sitter_adapter",
        "typescript_adapter",
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


CLI = load_cli_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global CLI
    load_cli_modules.cache_clear()
    CLI = load_cli_modules()


def runner() -> CliRunner:
    return CliRunner()


def test_cli_parse_works_for_parity_fixture_root() -> None:
    result = runner().invoke(CLI.app, ["parse", str(ROOT / "examples" / "parity"), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["scope"] == "project"
    assert payload["file_count"] == 3


def test_cli_parse_validate_and_map_work_for_python_parity_fixture() -> None:
    parity_path = str(ROOT / "examples" / "parity" / "python")

    parse_result = runner().invoke(CLI.app, ["parse", parity_path, "--json"])
    validate_result = runner().invoke(CLI.app, ["validate", parity_path, "--json"])
    map_result = runner().invoke(CLI.app, ["map", parity_path, "--json"])

    assert parse_result.exit_code == 0
    assert validate_result.exit_code == 0
    assert map_result.exit_code == 0

    parse_payload = json.loads(parse_result.output)
    validate_payload = json.loads(validate_result.output)
    map_payload = json.loads(map_result.output)

    assert parse_payload["ok"] is True
    assert validate_payload["ok"] is True
    assert map_payload["grace_version"] == "v1"


def test_cli_parse_validate_and_map_work_for_typescript_parity_fixture() -> None:
    parity_path = str(ROOT / "examples" / "parity" / "typescript")

    parse_result = runner().invoke(CLI.app, ["parse", parity_path, "--json"])
    validate_result = runner().invoke(CLI.app, ["validate", parity_path, "--json"])
    map_result = runner().invoke(CLI.app, ["map", parity_path, "--json"])

    assert parse_result.exit_code == 0
    assert validate_result.exit_code == 0
    assert map_result.exit_code == 0

    parse_payload = json.loads(parse_result.output)
    validate_payload = json.loads(validate_result.output)
    map_payload = json.loads(map_result.output)

    assert parse_payload["ok"] is True
    assert validate_payload["ok"] is True
    assert map_payload["grace_version"] == "v1"


def test_cli_parse_validate_and_map_work_for_go_parity_fixture() -> None:
    parity_path = str(ROOT / "examples" / "parity" / "go")

    parse_result = runner().invoke(CLI.app, ["parse", parity_path, "--json"])
    validate_result = runner().invoke(CLI.app, ["validate", parity_path, "--json"])
    map_result = runner().invoke(CLI.app, ["map", parity_path, "--json"])

    assert parse_result.exit_code == 0
    assert validate_result.exit_code == 0
    assert map_result.exit_code == 0

    parse_payload = json.loads(parse_result.output)
    validate_payload = json.loads(validate_result.output)
    map_payload = json.loads(map_result.output)

    assert parse_payload["ok"] is True
    assert validate_payload["ok"] is True
    assert map_payload["grace_version"] == "v1"
