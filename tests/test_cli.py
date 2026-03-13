from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
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
        "grace.validator",
        "grace.linter",
        "grace.map",
        "grace.patcher",
        "grace.plan",
        "grace.query",
        "grace.cli",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "validator", "linter", "map", "patcher", "plan", "query", "cli"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return (
        loaded["models"],
        loaded["parser"],
        loaded["validator"],
        loaded["linter"],
        loaded["map"],
        loaded["patcher"],
        loaded["plan"],
        loaded["cli"],
    )


MODELS, PARSER, VALIDATOR, LINTER, MAP, PATCHER, PLAN, CLI = load_cli_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER, VALIDATOR, LINTER, MAP, PATCHER, PLAN, CLI
    load_cli_modules.cache_clear()
    MODELS, PARSER, VALIDATOR, LINTER, MAP, PATCHER, PLAN, CLI = load_cli_modules()


def write_temp_python_file(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_cli_files"
    writable_dir.mkdir(parents=True, exist_ok=True)
    try:
        writable_dir.chmod(0o777)
    except OSError:
        pass
    path = writable_dir / name
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def write_temp_json_file(tmp_path: Path, payload: dict, name: str = "plan.json") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_cli_files"
    writable_dir.mkdir(parents=True, exist_ok=True)
    try:
        writable_dir.chmod(0o777)
    except OSError:
        pass
    path = writable_dir / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def module_header(
    *,
    module_id: str = "billing.pricing",
    purpose: str = "Determine pricing behavior.",
    interfaces: str = "apply_discount(price:int, percent:int) -> int",
    invariants: tuple[str, ...] = (
        "Discount percent must never be negative.",
        "Anchor ids remain stable for unchanged semantics.",
    ),
) -> str:
    invariant_lines = "\n".join(f"# @grace.invariant {value}" for value in invariants)
    return (
        f"# @grace.module {module_id}\n"
        f"# @grace.purpose {purpose}\n"
        f"# @grace.interfaces {interfaces}\n"
        f"{invariant_lines}\n"
    )


def function_block(
    *,
    anchor: str = "billing.pricing.apply_discount",
    complexity: str = "1",
    belief: str | None = None,
    links: str | None = None,
    signature: str = "def apply_discount(price: int, percent: int) -> int:",
    body: str = "    return price - ((price * percent) // 100)",
) -> str:
    lines = [
        f"# @grace.anchor {anchor}",
        f"# @grace.complexity {complexity}",
    ]
    if belief is not None:
        lines.append(f"# @grace.belief {belief}")
    if links is not None:
        lines.append(f"# @grace.links {links}")
    lines.extend([signature, body])
    return "\n".join(lines)


def make_file(*sections: str, header: str | None = None) -> str:
    active_header = header if header is not None else module_header()
    body = "\n\n".join(section.strip("\n") for section in sections)
    return f"{active_header.rstrip()}\n\n{body}\n"


def runner() -> CliRunner:
    return CliRunner()


def test_cli_parse_success(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")

    result = runner().invoke(CLI.app, ["parse", str(path)])

    assert result.exit_code == 0
    assert "Parsed module billing.pricing with 1 block(s)" in result.output


def test_cli_parse_success_json_output(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")

    result = runner().invoke(CLI.app, ["parse", "--json", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "parse"
    assert payload["module_id"] == "billing.pricing"
    assert payload["block_count"] == 1
    assert payload["file"]["module"]["module_id"] == "billing.pricing"


def test_cli_parse_failure(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, function_block(), name="pricing.py")

    result = runner().invoke(CLI.app, ["parse", str(path)])

    assert result.exit_code != 0
    assert "Parse failed" in result.output
    assert "missing_required_module_annotation" in result.output


def test_cli_parse_failure_json_output(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, function_block(), name="pricing.py")

    result = runner().invoke(CLI.app, ["parse", "--json", str(path)])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "parse"
    assert payload["stage"] == "parse"
    assert any(error["code"] == "missing_required_module_annotation" for error in payload["errors"])


def test_cli_validate_success(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")

    result = runner().invoke(CLI.app, ["validate", str(path)])

    assert result.exit_code == 0
    assert "Validated module billing.pricing successfully" in result.output


def test_cli_validate_success_json_output(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")

    result = runner().invoke(CLI.app, ["validate", "--json", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "validate"
    assert payload["validation"] == {"ok": True, "scope": "file"}


def test_cli_validate_failure(tmp_path: Path) -> None:
    path = write_temp_python_file(
        tmp_path,
        make_file(function_block(anchor="external.apply_discount")),
        name="pricing.py",
    )

    result = runner().invoke(CLI.app, ["validate", str(path)])

    assert result.exit_code != 0
    assert "Validation failed" in result.output
    assert "anchor_module_prefix_mismatch" in result.output


def test_cli_validate_failure_json_output(tmp_path: Path) -> None:
    path = write_temp_python_file(
        tmp_path,
        make_file(function_block(anchor="external.apply_discount")),
        name="pricing.py",
    )

    result = runner().invoke(CLI.app, ["validate", "--json", str(path)])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "validate"
    assert payload["stage"] == "validate"
    assert any(issue["code"] == "anchor_module_prefix_mismatch" for issue in payload["issues"])


def test_cli_lint_success(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")

    result = runner().invoke(CLI.app, ["lint", str(path)])

    assert result.exit_code == 0
    assert "Lint passed for module billing.pricing" in result.output


def test_cli_lint_success_json_output(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")

    result = runner().invoke(CLI.app, ["lint", "--json", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "lint"
    assert payload["warning_count"] == 0
    assert payload["warnings"] == []
    assert payload["clean"] is True


def test_cli_lint_warnings_keep_zero_exit_code(tmp_path: Path) -> None:
    path = write_temp_python_file(
        tmp_path,
        make_file(function_block(complexity="6", belief="maybe")),
        name="pricing.py",
    )

    result = runner().invoke(CLI.app, ["lint", str(path)])

    assert result.exit_code == 0
    assert "Lint warnings" in result.output
    assert "weak_belief" in result.output


def test_cli_lint_warnings_json_output_keeps_zero_exit_code(tmp_path: Path) -> None:
    path = write_temp_python_file(
        tmp_path,
        make_file(function_block(complexity="6", belief="maybe")),
        name="pricing.py",
    )

    result = runner().invoke(CLI.app, ["lint", "--json", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "lint"
    assert payload["warning_count"] >= 1
    assert payload["clean"] is False
    assert any(issue["code"] == "weak_belief" for issue in payload["warnings"])


def test_cli_map_success_with_json_output(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")

    result = runner().invoke(CLI.app, ["map", str(path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["grace_version"] == "v1"
    assert payload["modules"][0]["module_id"] == "billing.pricing"


def test_cli_patch_success(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )

    result = runner().invoke(CLI.app, ["patch", str(path), "billing.pricing.apply_discount", str(replacement_path)])

    assert result.exit_code == 0
    assert "Patched billing.pricing.apply_discount" in result.output
    assert "return 42" in path.read_text(encoding="utf-8")


def test_cli_patch_success_json_output(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )

    result = runner().invoke(CLI.app, ["patch", "--json", str(path), "billing.pricing.apply_discount", str(replacement_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "patch"
    assert payload["target"] == {
        "path": str(path),
        "anchor_id": "billing.pricing.apply_discount",
    }
    assert payload["anchor_id"] == "billing.pricing.apply_discount"
    assert payload["dry_run"] is False
    assert payload["identity_preserved"] is True
    assert payload["parse"]["status"] == "passed"
    assert payload["validate"]["status"] == "passed"
    assert payload["rollback_performed"] is False
    assert payload["before_hash"] != payload["after_hash"]
    assert "preview" in payload
    assert payload["warning_count"] == 0
    assert payload["file"]["blocks"][0]["anchor_id"] == "billing.pricing.apply_discount"


def test_cli_patch_dry_run_text_success_does_not_modify_file(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = path.read_text(encoding="utf-8")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )

    result = runner().invoke(
        CLI.app,
        ["patch", "--dry-run", str(path), "billing.pricing.apply_discount", str(replacement_path)],
    )

    assert result.exit_code == 0
    assert "Dry-run succeeded for billing.pricing.apply_discount" in result.output
    assert path.read_text(encoding="utf-8") == original_text


def test_cli_patch_preview_shows_diff_without_modifying_file(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = path.read_text(encoding="utf-8")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )

    result = runner().invoke(
        CLI.app,
        ["patch", "--preview", str(path), "billing.pricing.apply_discount", str(replacement_path)],
    )

    assert result.exit_code == 0
    assert "Patch preview for billing.pricing.apply_discount" in result.output
    assert "---" in result.output
    assert "+++" in result.output
    assert "return 42" in result.output
    assert path.read_text(encoding="utf-8") == original_text


def test_cli_patch_dry_run_json_output_is_structured_and_does_not_modify_file(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = path.read_text(encoding="utf-8")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )

    result = runner().invoke(
        CLI.app,
        ["patch", "--dry-run", "--json", str(path), "billing.pricing.apply_discount", str(replacement_path)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["identity_preserved"] is True
    assert payload["parse"]["status"] == "passed"
    assert payload["validate"]["status"] == "passed"
    assert payload["rollback_performed"] is False
    assert "return 42" in payload["preview"]
    assert path.read_text(encoding="utf-8") == original_text


def test_cli_patch_failure_on_unknown_anchor(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )

    result = runner().invoke(CLI.app, ["patch", str(path), "billing.pricing.unknown", str(replacement_path)])

    assert result.exit_code != 0
    assert "Patch failed at stage target_lookup" in result.output


def test_cli_patch_failure_on_unknown_anchor_json_output(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )

    result = runner().invoke(
        CLI.app,
        ["patch", "--json", str(path), "billing.pricing.unknown", str(replacement_path)],
    )

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "patch"
    assert payload["stage"] == "target_lookup"
    assert payload["rollback_performed"] is False
    assert payload["parse"]["status"] == "passed"


def test_cli_patch_failure_on_identity_mismatch(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.other_name\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )

    result = runner().invoke(CLI.app, ["patch", str(path), "billing.pricing.apply_discount", str(replacement_path)])

    assert result.exit_code != 0
    assert "Patch failed at stage identity" in result.output


def test_cli_patch_failure_on_identity_mismatch_json_output(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.other_name\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )

    result = runner().invoke(
        CLI.app,
        ["patch", "--json", str(path), "billing.pricing.apply_discount", str(replacement_path)],
    )

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "patch"
    assert payload["stage"] == "identity"
    assert payload["identity_preserved"] is False
    assert payload["rollback_performed"] is False


def test_cli_apply_plan_success_json_output(tmp_path: Path) -> None:
    pricing_path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )
    plan_path = write_temp_json_file(
        tmp_path,
        {
            "grace_version": "v1",
            "entries": [
                {
                    "path": str(pricing_path),
                    "anchor_id": "billing.pricing.apply_discount",
                    "operation": "replace_block",
                    "replacement_file": str(replacement_path),
                }
            ],
        },
        name="plan.json",
    )

    result = runner().invoke(CLI.app, ["apply-plan", "--json", str(plan_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "apply-plan"
    assert payload["scope"] == "project"
    assert payload["dry_run"] is False
    assert payload["preview"] is False
    assert payload["entry_count"] == 1
    assert payload["applied_count"] == 1
    assert payload["entries"][0]["result"]["ok"] is True
    assert "return 42" in pricing_path.read_text(encoding="utf-8")


def test_cli_apply_plan_dry_run_json_output_does_not_modify_file(tmp_path: Path) -> None:
    pricing_path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = pricing_path.read_text(encoding="utf-8")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )
    plan_path = write_temp_json_file(
        tmp_path,
        {
            "grace_version": "v1",
            "entries": [
                {
                    "path": str(pricing_path),
                    "anchor_id": "billing.pricing.apply_discount",
                    "operation": "replace_block",
                    "replacement_file": str(replacement_path),
                }
            ],
        },
        name="plan.json",
    )

    result = runner().invoke(CLI.app, ["apply-plan", "--dry-run", "--json", str(plan_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["preview"] is False
    assert payload["entries"][0]["result"]["dry_run"] is True
    assert pricing_path.read_text(encoding="utf-8") == original_text


def test_cli_apply_plan_dry_run_text_output_does_not_modify_file(tmp_path: Path) -> None:
    pricing_path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = pricing_path.read_text(encoding="utf-8")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )
    plan_path = write_temp_json_file(
        tmp_path,
        {
            "grace_version": "v1",
            "entries": [
                {
                    "path": str(pricing_path),
                    "anchor_id": "billing.pricing.apply_discount",
                    "operation": "replace_block",
                    "replacement_file": str(replacement_path),
                }
            ],
        },
        name="plan.json",
    )

    result = runner().invoke(CLI.app, ["apply-plan", "--dry-run", str(plan_path)])

    assert result.exit_code == 0
    assert "Dry-run succeeded for patch plan" in result.output
    assert pricing_path.read_text(encoding="utf-8") == original_text


def test_cli_apply_plan_preview_json_output_shows_previews_without_modifying_file(tmp_path: Path) -> None:
    pricing_path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = pricing_path.read_text(encoding="utf-8")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )
    plan_path = write_temp_json_file(
        tmp_path,
        {
            "grace_version": "v1",
            "entries": [
                {
                    "path": str(pricing_path),
                    "anchor_id": "billing.pricing.apply_discount",
                    "operation": "replace_block",
                    "replacement_file": str(replacement_path),
                }
            ],
        },
        name="plan.json",
    )

    result = runner().invoke(CLI.app, ["apply-plan", "--preview", "--json", str(plan_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["preview"] is True
    assert "---" in payload["entries"][0]["result"]["preview"]
    assert "return 42" in payload["entries"][0]["result"]["preview"]
    assert pricing_path.read_text(encoding="utf-8") == original_text


def test_cli_apply_plan_preview_text_output_shows_previews_without_modifying_file(tmp_path: Path) -> None:
    pricing_path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = pricing_path.read_text(encoding="utf-8")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )
    plan_path = write_temp_json_file(
        tmp_path,
        {
            "grace_version": "v1",
            "entries": [
                {
                    "path": str(pricing_path),
                    "anchor_id": "billing.pricing.apply_discount",
                    "operation": "replace_block",
                    "replacement_file": str(replacement_path),
                }
            ],
        },
        name="plan.json",
    )

    result = runner().invoke(CLI.app, ["apply-plan", "--preview", str(plan_path)])

    assert result.exit_code == 0
    assert "Patch plan preview:" in result.output
    assert "Entry 0: billing.pricing.apply_discount" in result.output
    assert "---" in result.output
    assert "return 42" in result.output
    assert pricing_path.read_text(encoding="utf-8") == original_text


def test_cli_apply_plan_failure_stops_on_first_failure_json_output(tmp_path: Path) -> None:
    pricing_path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    tax_path = write_temp_python_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.tax.apply_tax", signature="def apply_tax(amount: int) -> int:", body="    return amount"),
            header=module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
        ),
        name="tax.py",
    )
    original_pricing_text = pricing_path.read_text(encoding="utf-8")
    original_tax_text = tax_path.read_text(encoding="utf-8")
    replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        name="replacement.py",
    )
    failing_replacement_path = write_temp_python_file(
        tmp_path,
        (
            "# @grace.anchor billing.tax.missing_anchor\n"
            "# @grace.complexity 2\n"
            "def apply_tax(amount: int) -> int:\n"
            "    return amount + 1\n"
        ),
        name="failing_replacement.py",
    )
    plan_path = write_temp_json_file(
        tmp_path,
        {
            "grace_version": "v1",
            "entries": [
                {
                    "path": str(pricing_path),
                    "anchor_id": "billing.pricing.apply_discount",
                    "operation": "replace_block",
                    "replacement_file": str(replacement_path),
                },
                {
                    "path": str(tax_path),
                    "anchor_id": "billing.tax.missing_anchor",
                    "operation": "replace_block",
                    "replacement_file": str(failing_replacement_path),
                },
            ],
        },
        name="plan.json",
    )

    result = runner().invoke(CLI.app, ["apply-plan", "--json", str(plan_path)])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "apply-plan"
    assert payload["stage"] == "entry_failure"
    assert payload["dry_run"] is False
    assert payload["preview"] is False
    assert payload["applied_count"] == 1
    assert payload["failed_index"] == 1
    assert payload["failed_path"] == str(tax_path)
    assert payload["failed_anchor_id"] == "billing.tax.missing_anchor"
    assert payload["entries"][0]["result"]["ok"] is True
    assert payload["entries"][1]["result"]["ok"] is False
    assert pricing_path.read_text(encoding="utf-8") == original_pricing_text
    assert tax_path.read_text(encoding="utf-8") == original_tax_text


def test_cli_apply_plan_plan_load_failure_has_stable_taxonomy(tmp_path: Path) -> None:
    plan_path = write_temp_python_file(tmp_path, "{not-json", name="broken_plan.json")

    result = runner().invoke(CLI.app, ["apply-plan", "--json", str(plan_path)])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "apply-plan"
    assert payload["stage"] == "plan_load"
    assert payload["dry_run"] is False
    assert payload["preview"] is False


def test_cli_validate_command_is_thin_wrapper_over_core_apis(tmp_path: Path, monkeypatch) -> None:
    path = write_temp_python_file(tmp_path, "placeholder", name="pricing.py")
    calls: list[tuple[str, object]] = []
    stub_file = MODELS.GraceFileModel(
        path=path,
        module=MODELS.GraceModuleMetadata(
            module_id="billing.pricing",
            purpose="Determine pricing behavior.",
            interfaces="apply_discount(price:int, percent:int) -> int",
            invariants=("Discount percent must never be negative.",),
        ),
        blocks=(
            MODELS.GraceBlockMetadata(
                anchor_id="billing.pricing.apply_discount",
                kind=MODELS.BlockKind.FUNCTION,
                symbol_name="apply_discount",
                qualified_name="apply_discount",
                is_async=False,
                complexity=1,
                belief=None,
                links=(),
                line_start=1,
                line_end=2,
            ),
        ),
    )

    def fake_parse_python_file(received_path: Path):
        calls.append(("parse", received_path))
        return stub_file

    def fake_validate_file(received_file):
        calls.append(("validate", received_file))
        return VALIDATOR.ValidationSuccess(scope="file")

    monkeypatch.setattr(CLI, "parse_python_file", fake_parse_python_file)
    monkeypatch.setattr(CLI, "validate_file", fake_validate_file)

    result = runner().invoke(CLI.app, ["validate", str(path)])

    assert result.exit_code == 0
    assert calls == [("parse", path), ("validate", stub_file)]
