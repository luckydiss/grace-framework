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
        "grace.query",
        "grace.cli",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "validator", "linter", "map", "patcher", "query", "cli"):
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
        loaded["cli"],
    )


MODELS, PARSER, VALIDATOR, LINTER, MAP, PATCHER, CLI = load_cli_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER, VALIDATOR, LINTER, MAP, PATCHER, CLI
    load_cli_modules.cache_clear()
    MODELS, PARSER, VALIDATOR, LINTER, MAP, PATCHER, CLI = load_cli_modules()


def write_temp_python_file(base_dir: Path, relative_path: str, content: str) -> Path:
    path = base_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def module_header(
    *,
    module_id: str,
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
    anchor: str,
    complexity: str = "1",
    belief: str | None = None,
    links: str | None = None,
    signature: str,
    body: str,
) -> str:
    lines = [f"# @grace.anchor {anchor}", f"# @grace.complexity {complexity}"]
    if belief is not None:
        lines.append(f"# @grace.belief {belief}")
    if links is not None:
        lines.append(f"# @grace.links {links}")
    lines.extend([signature, body])
    return "\n".join(lines)


def make_file(header: str, *sections: str) -> str:
    body = "\n\n".join(section.strip("\n") for section in sections)
    return f"{header.rstrip()}\n\n{body}\n"


def runner() -> CliRunner:
    return CliRunner()


def create_repo_dir(tmp_path: Path) -> Path:
    repo_dir = tmp_path.parent / f"{tmp_path.name}_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    return repo_dir


def test_cli_parse_directory_json_success_and_ignores_non_grace_files(tmp_path: Path) -> None:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(
        repo_dir,
        "src/pricing.py",
        make_file(
            module_header(module_id="billing.pricing"),
            function_block(
                anchor="billing.pricing.apply_discount",
                signature="def apply_discount(price: int, percent: int) -> int:",
                body="    return price",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/tax.py",
        make_file(
            module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
            function_block(
                anchor="billing.tax.apply_tax",
                signature="def apply_tax(amount: int) -> int:",
                body="    return amount",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "tests/helper.py",
        (
            "FIXTURE = '''\n"
            "# @grace.module fixture.module\n"
            "# @grace.purpose Fixture only.\n"
            "# @grace.interfaces noop()\n"
            "# @grace.invariant Fixture data stays intentionally invalid for discovery tests.\n"
            "'''\n\n"
            "def helper() -> int:\n"
            "    return 1\n"
        ),
    )
    write_temp_python_file(
        repo_dir,
        ".venv/ignored.py",
        make_file(
            module_header(module_id="ignored.module"),
            function_block(
                anchor="ignored.module.should_not_be_seen",
                signature="def should_not_be_seen() -> int:",
                body="    return 0",
            ),
        ),
    )

    result = runner().invoke(CLI.app, ["parse", "--json", str(repo_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "parse"
    assert payload["scope"] == "project"
    assert payload["file_count"] == 2
    assert payload["module_count"] == 2
    assert {file_payload["module"]["module_id"] for file_payload in payload["files"]} == {
        "billing.pricing",
        "billing.tax",
    }


def test_cli_parse_directory_ignores_fixture_strings_that_are_not_top_level_module_headers(tmp_path: Path) -> None:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(
        repo_dir,
        "src/pricing.py",
        make_file(
            module_header(module_id="billing.pricing"),
            function_block(
                anchor="billing.pricing.apply_discount",
                signature="def apply_discount(price: int, percent: int) -> int:",
                body="    return price",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "tests/fixtures.py",
        (
            "BAD_FIXTURE = '''\n"
            "# @grace.module broken.fixture\n"
            "# @grace.purpose This should not be discovered.\n"
            "# @grace.interfaces noop()\n"
            "# @grace.invariant Fixture remains text, not a module header.\n"
            "\n"
            "# @grace.anchor broken.fixture.example\n"
            "# @grace.complexity 1\n"
            "def example() -> int:\n"
            "    return 0\n"
            "'''\n"
        ),
    )

    result = runner().invoke(CLI.app, ["parse", "--json", str(repo_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["file_count"] == 1
    assert [file_payload["module"]["module_id"] for file_payload in payload["files"]] == ["billing.pricing"]


def test_cli_parse_directory_json_failure_on_invalid_grace_candidate(tmp_path: Path) -> None:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(
        repo_dir,
        "src/pricing.py",
        make_file(
            module_header(module_id="billing.pricing"),
            function_block(
                anchor="billing.pricing.apply_discount",
                signature="def apply_discount(price: int, percent: int) -> int:",
                body="    return price",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/broken.py",
        (
            "# @grace.module billing.broken\n"
            "# @grace.purpose Broken candidate for parse failure coverage.\n"
            "# @grace.interfaces partial() -> int\n"
            "# @grace.invariant Broken candidates should still fail predictably once discovered.\n"
            "\n"
            "# @grace.anchor billing.broken.partial\n"
            "# @grace.complexity 6\n"
            "def partial() -> int:\n"
            "    return 0\n"
        ),
    )

    result = runner().invoke(CLI.app, ["parse", "--json", str(repo_dir)])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["scope"] == "project"
    assert payload["stage"] == "parse"
    assert payload["failed_file_count"] == 1
    assert any(error["path"].endswith("src\\broken.py") or error["path"].endswith("src/broken.py") for error in payload["errors"])


def test_cli_validate_directory_json_success_for_multiple_valid_files(tmp_path: Path) -> None:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(
        repo_dir,
        "src/pricing.py",
        make_file(
            module_header(
                module_id="billing.pricing",
                interfaces="choose_discount_strategy(customer_tier:str) -> int",
            ),
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="Pricing thresholds remain deterministic for the project baseline.",
                signature="def choose_discount_strategy(customer_tier: str) -> int:",
                body="    return 0",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/tax.py",
        make_file(
            module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
            function_block(
                anchor="billing.tax.apply_tax",
                signature="def apply_tax(amount: int) -> int:",
                body="    return amount",
            ),
        ),
    )

    result = runner().invoke(CLI.app, ["validate", "--json", str(repo_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "validate"
    assert payload["scope"] == "project"
    assert payload["validation"] == {"ok": True, "scope": "project"}


def test_cli_validate_directory_json_allows_cross_file_links_when_target_exists(tmp_path: Path) -> None:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(
        repo_dir,
        "src/pricing.py",
        make_file(
            module_header(
                module_id="billing.pricing",
                interfaces="choose_discount_strategy(customer_tier:str) -> int",
            ),
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="Pricing thresholds remain deterministic for the project baseline.",
                links="billing.tax.apply_tax",
                signature="def choose_discount_strategy(customer_tier: str) -> int:",
                body="    return 0",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/tax.py",
        make_file(
            module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
            function_block(
                anchor="billing.tax.apply_tax",
                signature="def apply_tax(amount: int) -> int:",
                body="    return amount",
            ),
        ),
    )

    result = runner().invoke(CLI.app, ["validate", "--json", str(repo_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["scope"] == "project"


def test_cli_validate_directory_json_failure_for_project_issue(tmp_path: Path) -> None:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(
        repo_dir,
        "src/one.py",
        make_file(
            module_header(module_id="billing.one"),
            function_block(
                anchor="billing.shared.anchor",
                signature="def first() -> int:",
                body="    return 1",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/two.py",
        make_file(
            module_header(module_id="billing.two"),
            function_block(
                anchor="billing.shared.anchor",
                signature="def second() -> int:",
                body="    return 2",
            ),
        ),
    )

    result = runner().invoke(CLI.app, ["validate", "--json", str(repo_dir)])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["scope"] == "project"
    assert payload["stage"] == "validate"
    assert any(issue["code"] == "duplicate_anchor_id" for issue in payload["issues"])


def test_cli_lint_directory_json_warnings_keep_zero_exit_code(tmp_path: Path) -> None:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(
        repo_dir,
        "src/pricing.py",
        make_file(
            module_header(module_id="billing.pricing", purpose="todo", invariants=("Only placeholder",)),
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="maybe",
                signature="def choose_discount_strategy(customer_tier: str) -> int:",
                body="    return 0",
            ),
        ),
    )

    result = runner().invoke(CLI.app, ["lint", "--json", str(repo_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["scope"] == "project"
    assert payload["warning_count"] >= 1
    assert payload["clean"] is False
    assert any(issue["code"] == "weak_belief" for issue in payload["warnings"])


def test_cli_map_directory_json_success(tmp_path: Path) -> None:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(
        repo_dir,
        "src/pricing.py",
        make_file(
            module_header(module_id="billing.pricing"),
            function_block(
                anchor="billing.pricing.apply_discount",
                signature="def apply_discount(price: int, percent: int) -> int:",
                body="    return price",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/tax.py",
        make_file(
            module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
            function_block(
                anchor="billing.tax.apply_tax",
                signature="def apply_tax(amount: int) -> int:",
                body="    return amount",
            ),
        ),
    )

    result = runner().invoke(CLI.app, ["map", "--json", str(repo_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["grace_version"] == "v1"
    assert len(payload["modules"]) == 2
    assert len(payload["anchors"]) == 2


def test_cli_map_directory_json_includes_cross_file_anchor_link_edge(tmp_path: Path) -> None:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(
        repo_dir,
        "src/pricing.py",
        make_file(
            module_header(
                module_id="billing.pricing",
                interfaces="choose_discount_strategy(customer_tier:str) -> int",
            ),
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="Pricing thresholds remain deterministic for the project baseline.",
                links="billing.tax.apply_tax",
                signature="def choose_discount_strategy(customer_tier: str) -> int:",
                body="    return 0",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/tax.py",
        make_file(
            module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
            function_block(
                anchor="billing.tax.apply_tax",
                signature="def apply_tax(amount: int) -> int:",
                body="    return amount",
            ),
        ),
    )

    result = runner().invoke(CLI.app, ["map", "--json", str(repo_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert {
        (edge["type"], edge["source"], edge["target"])
        for edge in payload["edges"]
    } >= {
        ("anchor_links_to_anchor", "billing.pricing.choose_discount_strategy", "billing.tax.apply_tax"),
    }


def test_cli_directory_json_discovery_failure_when_no_grace_files_found(tmp_path: Path) -> None:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(repo_dir, "src/plain.py", "def helper() -> int:\n    return 1\n")

    result = runner().invoke(CLI.app, ["validate", "--json", str(repo_dir)])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["stage"] == "discovery"
    assert payload["scope"] == "project"
