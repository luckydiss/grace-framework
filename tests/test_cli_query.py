from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
import types
from functools import lru_cache
from pathlib import Path

from click.testing import CliRunner


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_cli_modules():
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

    return loaded["cli"]


CLI = load_cli_modules()


def runner() -> CliRunner:
    return CliRunner()


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


def create_repo_dir(tmp_path: Path) -> Path:
    repo_dir = tmp_path.parent / f"{tmp_path.name}_query_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    return repo_dir


def build_query_repo(tmp_path: Path) -> Path:
    repo_dir = create_repo_dir(tmp_path)
    write_temp_python_file(
        repo_dir,
        "src/pricing.py",
        make_file(
            module_header(
                module_id="billing.pricing",
                interfaces="apply_discount(price:int, percent:int) -> int; choose_discount_strategy(customer_tier:str) -> int",
            ),
            function_block(
                anchor="billing.pricing.apply_discount",
                signature="def apply_discount(price: int, percent: int) -> int:",
                body="    return price",
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
                links="billing.audit.record_tax",
                signature="def apply_tax(amount: int) -> int:",
                body="    return amount",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/audit.py",
        make_file(
            module_header(module_id="billing.audit", interfaces="record_tax(amount:int) -> None"),
            function_block(
                anchor="billing.audit.record_tax",
                signature="def record_tax(amount: int) -> None:",
                body="    return None",
            ),
        ),
    )
    return repo_dir


def test_cli_query_modules_json_returns_deterministic_order(tmp_path: Path) -> None:
    repo_dir = build_query_repo(tmp_path)

    result = runner().invoke(CLI.app, ["query", "modules", "--json", str(repo_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "query"
    assert payload["query"] == "modules"
    assert payload["query_scope"] == "collection"
    assert [module["module_id"] for module in payload["modules"]] == [
        "billing.audit",
        "billing.pricing",
        "billing.tax",
    ]


def test_cli_query_anchors_json_supports_module_filter(tmp_path: Path) -> None:
    repo_dir = build_query_repo(tmp_path)

    result = runner().invoke(CLI.app, ["query", "anchors", "--module", "billing.pricing", "--json", str(repo_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["query"] == "anchors"
    assert payload["query_scope"] == "collection"
    assert payload["module_id"] == "billing.pricing"
    assert [anchor["anchor_id"] for anchor in payload["anchors"]] == [
        "billing.pricing.apply_discount",
        "billing.pricing.choose_discount_strategy",
    ]


def test_cli_query_anchor_json_returns_anchor_scoped_payload(tmp_path: Path) -> None:
    repo_dir = build_query_repo(tmp_path)

    result = runner().invoke(CLI.app, ["query", "anchor", "--json", str(repo_dir), "billing.tax.apply_tax"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["query"] == "anchor"
    assert payload["query_scope"] == "anchor"
    assert payload["anchor"]["anchor_id"] == "billing.tax.apply_tax"


def test_cli_query_links_json_returns_outgoing_targets(tmp_path: Path) -> None:
    repo_dir = build_query_repo(tmp_path)

    result = runner().invoke(CLI.app, ["query", "links", "--json", str(repo_dir), "billing.pricing.choose_discount_strategy"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["query"] == "links"
    assert [anchor["anchor_id"] for anchor in payload["links"]] == ["billing.tax.apply_tax"]


def test_cli_query_dependents_json_returns_incoming_sources(tmp_path: Path) -> None:
    repo_dir = build_query_repo(tmp_path)

    result = runner().invoke(CLI.app, ["query", "dependents", "--json", str(repo_dir), "billing.tax.apply_tax"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["query"] == "dependents"
    assert [anchor["anchor_id"] for anchor in payload["dependents"]] == ["billing.pricing.choose_discount_strategy"]


def test_cli_query_neighbors_json_returns_union_of_immediate_neighbors(tmp_path: Path) -> None:
    repo_dir = build_query_repo(tmp_path)

    result = runner().invoke(CLI.app, ["query", "neighbors", "--json", str(repo_dir), "billing.tax.apply_tax"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["query"] == "neighbors"
    assert [anchor["anchor_id"] for anchor in payload["neighbors"]] == [
        "billing.audit.record_tax",
        "billing.pricing.choose_discount_strategy",
    ]


def test_cli_query_unknown_anchor_has_stable_query_failure(tmp_path: Path) -> None:
    repo_dir = build_query_repo(tmp_path)

    result = runner().invoke(CLI.app, ["query", "anchor", "--json", str(repo_dir), "billing.unknown.anchor"])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "query"
    assert payload["query"] == "anchor"
    assert payload["query_scope"] == "anchor"
    assert payload["stage"] == "query"
    assert payload["anchor_id"] == "billing.unknown.anchor"
