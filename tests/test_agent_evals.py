from __future__ import annotations

import importlib.util
import json
import sys
import types
from functools import lru_cache
from pathlib import Path

from click.testing import CliRunner


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_cli_module():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
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


def runner() -> CliRunner:
    return CliRunner()


def invoke_json(*args: str):
    result = runner().invoke(CLI.app, list(args))
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def build_patch_eval_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    eval_dir = tmp_path.parent / f"{tmp_path.name}_agent_eval"
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

    plan_path = eval_dir / "self_hosting_eval.plan.json"
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


def compute_eval_metrics(tmp_path: Path) -> dict[str, float]:
    scenarios = (
        {
            "anchor_id": "grace.map.build_file_map",
            "expected_module_id": "grace.map",
            "expected_direct_dependents": ("grace.cli.read_command",),
            "expected_plan_targets": ("grace.cli.read_command",),
        },
        {
            "anchor_id": "grace.query.query_neighbors",
            "expected_module_id": "grace.query",
            "expected_direct_dependents": (
                "grace.cli.query_neighbors_command",
                "grace.read.build_anchor_neighbors",
            ),
            "expected_plan_targets": (
                "grace.cli.query_neighbors_command",
                "grace.read.build_anchor_neighbors",
            ),
        },
    )

    anchor_hits = 0
    patch_attempts = 0
    patch_successes = 0
    rollback_events = 0
    touched_files = 0
    unnecessary_file_touches = 0

    for scenario in scenarios:
        read_payload = invoke_json("read", "grace", scenario["anchor_id"], "--json")
        if read_payload["data"]["module_id"] == scenario["expected_module_id"]:
            anchor_hits += 1

        impact_payload = invoke_json("impact", "grace", scenario["anchor_id"], "--json")
        assert tuple(item["anchor_id"] for item in impact_payload["data"]["direct_dependents"]) == scenario[
            "expected_direct_dependents"
        ]

        plan_payload = invoke_json("plan", "impact", "grace", scenario["anchor_id"], "--json")
        assert tuple(item["anchor_id"] for item in plan_payload["data"]["suggested_operations"]) == scenario[
            "expected_plan_targets"
        ]

    replacement_path, plan_path = build_patch_eval_artifacts(tmp_path)

    patch_payload = invoke_json(
        "patch",
        str(ROOT / "grace" / "map.py"),
        "grace.map.build_file_map",
        str(replacement_path),
        "--dry-run",
        "--json",
    )
    patch_attempts += 1
    patch_successes += int(patch_payload["ok"] is True)
    rollback_events += int(patch_payload["rollback_performed"] is True)
    touched_files += 1
    unnecessary_file_touches += int(Path(patch_payload["path"]).resolve() != (ROOT / "grace" / "map.py").resolve())

    apply_plan_payload = invoke_json("apply-plan", str(plan_path), "--dry-run", "--preview", "--json")
    patch_attempts += 1
    patch_successes += int(apply_plan_payload["ok"] is True)
    rollback_events += sum(int(entry["result"]["rollback_performed"] is True) for entry in apply_plan_payload["entries"])
    touched_paths = {Path(entry["path"]).resolve() for entry in apply_plan_payload["entries"]}
    expected_paths = {(ROOT / "grace" / "map.py").resolve()}
    touched_files += len(touched_paths)
    unnecessary_file_touches += len(touched_paths - expected_paths)

    return {
        "anchor_selection_accuracy": anchor_hits / len(scenarios),
        "patch_apply_plan_success_rate": patch_successes / patch_attempts,
        "rollback_rate": rollback_events / patch_attempts,
        "unnecessary_file_touch_rate": unnecessary_file_touches / touched_files if touched_files else 0.0,
    }


def test_self_hosted_agent_eval_metrics_are_stable(tmp_path: Path) -> None:
    metrics = compute_eval_metrics(tmp_path)

    assert metrics == {
        "anchor_selection_accuracy": 1.0,
        "patch_apply_plan_success_rate": 1.0,
        "rollback_rate": 0.0,
        "unnecessary_file_touch_rate": 0.0,
    }


def test_self_hosted_agent_workflow_commands_succeed() -> None:
    map_payload = invoke_json("map", "grace", "--json")
    query_payload = invoke_json("query", "anchors", "grace", "--json")
    read_payload = invoke_json("read", "grace", "grace.map.build_file_map", "--json")
    impact_payload = invoke_json("impact", "grace", "grace.map.build_file_map", "--json")
    plan_payload = invoke_json("plan", "impact", "grace", "grace.map.build_file_map", "--json")
    validate_payload = invoke_json("validate", "grace", "--json")
    lint_payload = invoke_json("lint", "grace", "--json")

    assert len(map_payload["modules"]) >= 1
    assert query_payload["count"] >= 1
    assert read_payload["data"]["module_id"] == "grace.map"
    assert [item["anchor_id"] for item in impact_payload["data"]["direct_dependents"]] == ["grace.cli.read_command"]
    assert [item["anchor_id"] for item in plan_payload["data"]["suggested_operations"]] == ["grace.cli.read_command"]
    assert validate_payload["validation"] == {"ok": True, "scope": "project"}
    assert lint_payload["ok"] is True
