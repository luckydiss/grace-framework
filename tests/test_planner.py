from __future__ import annotations

import importlib.util
import sys
import textwrap
import types
from functools import lru_cache
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_planner_modules():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.map",
        "grace.impact",
        "grace.planner",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "map", "impact", "planner"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["models"], loaded["parser"], loaded["map"], loaded["impact"], loaded["planner"]


MODELS, PARSER, MAP, IMPACT, PLANNER = load_planner_modules()


def module_header(
    *,
    module_id: str,
    purpose: str = "Determine pricing behavior.",
    interfaces: str = "run() -> None",
    invariants: tuple[str, ...] = (
        "Anchor ids remain stable for unchanged semantics.",
        "Dependencies are explicit through grace.links.",
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


def parse_file(tmp_path: Path, content: str, name: str) -> MODELS.GraceFileModel:
    repo_dir = tmp_path.parent / f"{tmp_path.name}_planner_files"
    repo_dir.mkdir(parents=True, exist_ok=True)
    path = repo_dir / name
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return PARSER.parse_python_file(path)


def build_planner_map(tmp_path: Path):
    pricing = parse_file(
        tmp_path,
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
        name="pricing.py",
    )
    reporting = parse_file(
        tmp_path,
        make_file(
            module_header(module_id="billing.reporting", interfaces="build_tax_report() -> int"),
            function_block(
                anchor="billing.reporting.build_tax_report",
                links="billing.tax.apply_tax",
                signature="def build_tax_report() -> int:",
                body="    return 1",
            ),
        ),
        name="reporting.py",
    )
    audit = parse_file(
        tmp_path,
        make_file(
            module_header(module_id="billing.audit", interfaces="record_tax_trace() -> None"),
            function_block(
                anchor="billing.audit.record_tax_trace",
                links="billing.reporting.build_tax_report",
                signature="def record_tax_trace() -> None:",
                body="    return None",
            ),
        ),
        name="audit.py",
    )
    tax = parse_file(
        tmp_path,
        make_file(
            module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
            function_block(
                anchor="billing.tax.apply_tax",
                signature="def apply_tax(amount: int) -> int:",
                body="    return amount",
            ),
        ),
        name="tax.py",
    )
    return MAP.build_project_map([audit, pricing, tax, reporting])


def test_plan_from_impact_returns_direct_dependents_as_replace_block_operations(tmp_path: Path) -> None:
    grace_map = build_planner_map(tmp_path)

    proposal = PLANNER.plan_from_impact(grace_map, "billing.tax.apply_tax")

    assert proposal.target_anchor_id == "billing.tax.apply_tax"
    assert [operation.anchor_id for operation in proposal.suggested_operations] == [
        "billing.pricing.choose_discount_strategy",
        "billing.reporting.build_tax_report",
    ]
    assert all(operation.operation == "replace_block" for operation in proposal.suggested_operations)


def test_plan_from_impact_is_deterministic(tmp_path: Path) -> None:
    grace_map = build_planner_map(tmp_path)

    first = PLANNER.plan_from_impact(grace_map, "billing.tax.apply_tax")
    second = PLANNER.plan_from_impact(grace_map, "billing.tax.apply_tax")

    assert first.model_dump(mode="python") == second.model_dump(mode="python")


def test_plan_from_impact_excludes_non_direct_transitive_dependents(tmp_path: Path) -> None:
    grace_map = build_planner_map(tmp_path)

    proposal = PLANNER.plan_from_impact(grace_map, "billing.tax.apply_tax")

    assert [operation.anchor_id for operation in proposal.suggested_operations] == [
        "billing.pricing.choose_discount_strategy",
        "billing.reporting.build_tax_report",
    ]
    assert "billing.audit.record_tax_trace" not in [operation.anchor_id for operation in proposal.suggested_operations]


def test_plan_from_impact_can_return_empty_plan(tmp_path: Path) -> None:
    grace_map = build_planner_map(tmp_path)

    proposal = PLANNER.plan_from_impact(grace_map, "billing.audit.record_tax_trace")

    assert proposal.target_anchor_id == "billing.audit.record_tax_trace"
    assert proposal.suggested_operations == ()


def test_plan_from_impact_raises_for_unknown_anchor(tmp_path: Path) -> None:
    grace_map = build_planner_map(tmp_path)

    with pytest.raises(PLANNER.PlannerLookupError):
        PLANNER.plan_from_impact(grace_map, "billing.unknown.anchor")
