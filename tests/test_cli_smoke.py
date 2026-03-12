from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write_temp_file(tmp_path: Path, content: str, name: str) -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_cli_smoke_files"
    writable_dir.mkdir(parents=True, exist_ok=True)
    try:
        writable_dir.chmod(0o777)
    except OSError:
        pass
    path = writable_dir / name
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def write_repo_file(repo_dir: Path, relative_path: str, content: str) -> Path:
    path = repo_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def module_header() -> str:
    return (
        "# @grace.module billing.pricing\n"
        "# @grace.purpose Determine pricing behavior.\n"
        "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
        "# @grace.invariant Discount percent must never be negative.\n"
        "# @grace.invariant Anchor ids remain stable for unchanged semantics.\n"
    )


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "grace.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_smoke_end_to_end(tmp_path: Path) -> None:
    target_path = write_temp_file(
        tmp_path,
        (
            module_header()
            + "\n"
            + "# @grace.anchor billing.pricing.apply_discount\n"
            + "# @grace.complexity 2\n"
            + "def apply_discount(price: int, percent: int) -> int:\n"
            + "    return price - ((price * percent) // 100)\n"
        ),
        "pricing.py",
    )
    replacement_path = write_temp_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    discounted = price - ((price * percent) // 100)\n"
            "    return max(discounted, 0)\n"
        ),
        "apply_discount.replacement.pyfrag",
    )

    parse_result = run_cli("parse", str(target_path))
    validate_result = run_cli("validate", str(target_path))
    lint_result = run_cli("lint", str(target_path))
    map_result = run_cli("map", str(target_path), "--json")
    patch_result = run_cli("patch", str(target_path), "billing.pricing.apply_discount", str(replacement_path))
    reparse_result = run_cli("parse", str(target_path))

    assert parse_result.returncode == 0
    assert "Parsed module billing.pricing with 1 block(s)" in parse_result.stdout

    assert validate_result.returncode == 0
    assert "Validated module billing.pricing successfully" in validate_result.stdout

    assert lint_result.returncode == 0
    assert "Lint passed for module billing.pricing" in lint_result.stdout

    assert map_result.returncode == 0
    payload = json.loads(map_result.stdout)
    assert payload["modules"][0]["module_id"] == "billing.pricing"
    assert payload["anchors"][0]["anchor_id"] == "billing.pricing.apply_discount"

    assert patch_result.returncode == 0
    assert "Patched billing.pricing.apply_discount" in patch_result.stdout
    assert "return max(discounted, 0)" in target_path.read_text(encoding="utf-8")

    assert reparse_result.returncode == 0
    assert "Parsed module billing.pricing with 1 block(s)" in reparse_result.stdout


def test_cli_smoke_apply_plan_end_to_end(tmp_path: Path) -> None:
    target_path = write_temp_file(
        tmp_path,
        (
            module_header()
            + "\n"
            + "# @grace.anchor billing.pricing.apply_discount\n"
            + "# @grace.complexity 2\n"
            + "def apply_discount(price: int, percent: int) -> int:\n"
            + "    return price - ((price * percent) // 100)\n"
        ),
        "pricing.py",
    )
    replacement_path = write_temp_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        "apply_discount.replacement.pyfrag",
    )
    plan_path = write_temp_file(
        tmp_path,
        json.dumps(
            {
                "grace_version": "v1",
                "entries": [
                    {
                        "path": str(target_path),
                        "anchor_id": "billing.pricing.apply_discount",
                        "operation": "replace_block",
                        "replacement_file": str(replacement_path),
                    }
                ],
            },
            indent=2,
        ),
        "apply_discount.plan.json",
    )

    result = run_cli("apply-plan", str(plan_path), "--json")
    validate_result = run_cli("validate", str(target_path), "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "apply-plan"
    assert payload["applied_count"] == 1
    assert "return 42" in target_path.read_text(encoding="utf-8")

    assert validate_result.returncode == 0
    validate_payload = json.loads(validate_result.stdout)
    assert validate_payload["ok"] is True


def test_cli_smoke_repo_level_json_end_to_end(tmp_path: Path) -> None:
    repo_dir = tmp_path.parent / f"{tmp_path.name}_grace_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    write_repo_file(
        repo_dir,
        "src/pricing.py",
        (
            module_header()
            + "\n"
            + "# @grace.anchor billing.pricing.apply_discount\n"
            + "# @grace.complexity 2\n"
            + "def apply_discount(price: int, percent: int) -> int:\n"
            + "    return price - ((price * percent) // 100)\n"
        ),
    )
    write_repo_file(
        repo_dir,
        "src/tax.py",
        (
            "# @grace.module billing.tax\n"
            "# @grace.purpose Apply taxes.\n"
            "# @grace.interfaces apply_tax(amount:int) -> int\n"
            "# @grace.invariant Tax amount must never be negative.\n"
            "# @grace.invariant Anchor ids remain stable for unchanged semantics.\n\n"
            "# @grace.anchor billing.tax.apply_tax\n"
            "# @grace.complexity 2\n"
            "def apply_tax(amount: int) -> int:\n"
            "    return amount\n"
        ),
    )

    parse_result = run_cli("parse", str(repo_dir), "--json")
    validate_result = run_cli("validate", str(repo_dir), "--json")
    lint_result = run_cli("lint", str(repo_dir), "--json")
    map_result = run_cli("map", str(repo_dir), "--json")

    assert parse_result.returncode == 0
    parse_payload = json.loads(parse_result.stdout)
    assert parse_payload["ok"] is True
    assert parse_payload["scope"] == "project"
    assert parse_payload["file_count"] == 2

    assert validate_result.returncode == 0
    validate_payload = json.loads(validate_result.stdout)
    assert validate_payload["ok"] is True
    assert validate_payload["scope"] == "project"

    assert lint_result.returncode == 0
    lint_payload = json.loads(lint_result.stdout)
    assert lint_payload["ok"] is True
    assert lint_payload["scope"] == "project"

    assert map_result.returncode == 0
    map_payload = json.loads(map_result.stdout)
    assert len(map_payload["modules"]) == 2
