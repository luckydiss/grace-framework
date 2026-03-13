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


def invoke_json(*args: str) -> dict:
    result = runner().invoke(CLI.app, list(args))
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def writable_eval_dir(tmp_path: Path) -> Path:
    eval_dir = tmp_path.parent / f"{tmp_path.name}_protocol_freeze"
    eval_dir.mkdir(parents=True, exist_ok=True)
    return eval_dir


def test_protocol_freeze_self_hosted_json_envelopes_remain_stable(tmp_path: Path) -> None:
    eval_dir = writable_eval_dir(tmp_path)
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

    plan_path = eval_dir / "protocol_freeze.plan.json"
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

    parse_payload = invoke_json("parse", "grace", "--json")
    validate_payload = invoke_json("validate", "grace", "--json")
    lint_payload = invoke_json("lint", "grace", "--json")
    read_payload = invoke_json("read", "grace", "grace.map.build_file_map", "--json")
    impact_payload = invoke_json("impact", "grace", "grace.map.build_file_map", "--json")
    plan_payload = invoke_json("plan", "impact", "grace", "grace.map.build_file_map", "--json")
    patch_payload = invoke_json(
        "patch",
        str(ROOT / "grace" / "map.py"),
        "grace.map.build_file_map",
        str(replacement_path),
        "--dry-run",
        "--preview",
        "--json",
    )
    apply_plan_payload = invoke_json("apply-plan", str(plan_path), "--dry-run", "--preview", "--json")

    assert {"ok", "command", "scope", "path", "file_count", "module_count", "block_count", "files"} <= set(parse_payload)
    assert {"ok", "command", "scope", "path", "validation", "file_count", "module_count", "block_count"} <= set(
        validate_payload
    )
    assert {"ok", "command", "scope", "path", "warning_count", "warnings", "clean"} <= set(lint_payload)
    assert {"ok", "command", "target", "data"} <= set(read_payload)
    assert {"anchor_id", "module_id", "file_path", "line_start", "line_end", "annotations", "code", "links", "neighbors"} <= set(
        read_payload["data"]
    )
    assert {"ok", "command", "target", "data"} <= set(impact_payload)
    assert {"direct_dependents", "transitive_dependents", "affected_modules"} <= set(impact_payload["data"])
    assert {"ok", "command", "mode", "target", "data"} <= set(plan_payload)
    assert {"suggested_operations"} <= set(plan_payload["data"])
    assert {
        "ok",
        "command",
        "scope",
        "target",
        "path",
        "anchor_id",
        "dry_run",
        "identity_preserved",
        "parse",
        "validate",
        "lint_warnings",
        "warning_count",
        "rollback_performed",
        "before_hash",
        "after_hash",
        "preview",
        "file",
    } <= set(patch_payload)
    assert {"ok", "command", "scope", "plan_path", "dry_run", "preview", "entry_count", "applied_count", "entries"} <= set(
        apply_plan_payload
    )


def test_protocol_freeze_repo_root_parse_and_map_are_deterministic() -> None:
    first_parse = invoke_json("parse", ".", "--json")
    second_parse = invoke_json("parse", ".", "--json")
    first_map = invoke_json("map", ".", "--json")
    second_map = invoke_json("map", ".", "--json")

    assert first_parse == second_parse
    assert first_map == second_map
    assert first_parse["scope"] == "project"
    assert first_parse["file_count"] >= 1
    assert set(first_map) == {"grace_version", "modules", "anchors", "edges"}
    assert first_map["modules"]
    assert first_map["anchors"]
    assert first_map["edges"]


def test_protocol_freeze_repo_root_validate_and_lint_succeed_under_configured_scope() -> None:
    validate_payload = invoke_json("validate", ".", "--json")
    lint_payload = invoke_json("lint", ".", "--json")

    assert validate_payload["ok"] is True
    assert validate_payload["scope"] == "project"
    assert validate_payload["validation"] == {"ok": True, "scope": "project"}

    assert lint_payload["ok"] is True
    assert lint_payload["scope"] == "project"
    assert lint_payload["warning_count"] >= 0
