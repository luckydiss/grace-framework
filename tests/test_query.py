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
def load_query_modules():
    for module_name in ("grace", "grace.models", "grace.parser", "grace.map", "grace.query"):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "map", "query"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["models"], loaded["parser"], loaded["map"], loaded["query"]


MODELS, PARSER, MAP, QUERY = load_query_modules()


def write_temp_python_file(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_query_files"
    writable_dir.mkdir(parents=True, exist_ok=True)
    try:
        writable_dir.chmod(0o777)
    except OSError:
        pass
    path = writable_dir / name
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def module_header(
    *,
    module_id: str = "billing.pricing",
    purpose: str = "Determine pricing behavior.",
    interfaces: str = "apply_discount(price:int, percent:int) -> int",
    invariants: tuple[str, ...] = ("Discount percent must never be negative.",),
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
    return PARSER.parse_python_file(write_temp_python_file(tmp_path, content, name=name))


def build_project_map(tmp_path: Path):
    pricing = parse_file(
        tmp_path,
        make_file(
            module_header(
                module_id="billing.pricing",
                interfaces="apply_discount(price:int, percent:int) -> int; choose_discount_strategy(customer_tier:str) -> int",
                invariants=(
                    "Discount percent must never be negative.",
                    "Anchor ids remain stable unless pricing semantics change.",
                ),
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
        name="pricing.py",
    )
    tax = parse_file(
        tmp_path,
        make_file(
            module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
            function_block(
                anchor="billing.tax.apply_tax",
                links="billing.audit.record_tax",
                signature="def apply_tax(amount: int) -> int:",
                body="    return amount",
            ),
        ),
        name="tax.py",
    )
    audit = parse_file(
        tmp_path,
        make_file(
            module_header(module_id="billing.audit", interfaces="record_tax(amount:int) -> None"),
            function_block(
                anchor="billing.audit.record_tax",
                signature="def record_tax(amount: int) -> None:",
                body="    return None",
            ),
        ),
        name="audit.py",
    )
    return MAP.build_project_map([tax, audit, pricing])


def test_query_modules_returns_deterministic_module_order(tmp_path: Path) -> None:
    grace_map = build_project_map(tmp_path)

    modules = QUERY.query_modules(grace_map)

    assert [module.module_id for module in modules] == [
        "billing.audit",
        "billing.pricing",
        "billing.tax",
    ]


def test_query_anchors_returns_deterministic_anchor_order_and_module_filter(tmp_path: Path) -> None:
    grace_map = build_project_map(tmp_path)

    anchors = QUERY.query_anchors(grace_map)
    pricing_anchors = QUERY.query_anchors(grace_map, module_id="billing.pricing")

    assert [anchor.anchor_id for anchor in anchors] == [
        "billing.audit.record_tax",
        "billing.pricing.apply_discount",
        "billing.pricing.choose_discount_strategy",
        "billing.tax.apply_tax",
    ]
    assert [anchor.anchor_id for anchor in pricing_anchors] == [
        "billing.pricing.apply_discount",
        "billing.pricing.choose_discount_strategy",
    ]


def test_query_anchor_returns_exact_anchor_record(tmp_path: Path) -> None:
    grace_map = build_project_map(tmp_path)

    anchor = QUERY.query_anchor(grace_map, "billing.tax.apply_tax")

    assert anchor.anchor_id == "billing.tax.apply_tax"
    assert anchor.module_id == "billing.tax"
    assert anchor.links == ("billing.audit.record_tax",)


def test_query_links_returns_explicit_outgoing_targets(tmp_path: Path) -> None:
    grace_map = build_project_map(tmp_path)

    links = QUERY.query_links(grace_map, "billing.pricing.choose_discount_strategy")

    assert [anchor.anchor_id for anchor in links] == ["billing.tax.apply_tax"]


def test_query_dependents_returns_incoming_sources(tmp_path: Path) -> None:
    grace_map = build_project_map(tmp_path)

    dependents = QUERY.query_dependents(grace_map, "billing.tax.apply_tax")

    assert [anchor.anchor_id for anchor in dependents] == ["billing.pricing.choose_discount_strategy"]


def test_query_neighbors_returns_union_of_incoming_and_outgoing_sorted(tmp_path: Path) -> None:
    grace_map = build_project_map(tmp_path)

    neighbors = QUERY.query_neighbors(grace_map, "billing.tax.apply_tax")

    assert [anchor.anchor_id for anchor in neighbors] == [
        "billing.audit.record_tax",
        "billing.pricing.choose_discount_strategy",
    ]


def test_query_unknown_anchor_raises_lookup_error(tmp_path: Path) -> None:
    grace_map = build_project_map(tmp_path)

    with pytest.raises(QUERY.QueryLookupError):
        QUERY.query_anchor(grace_map, "billing.unknown.anchor")


def test_query_layer_does_not_introduce_new_identity(tmp_path: Path) -> None:
    grace_map = build_project_map(tmp_path)

    all_anchor_ids = {anchor.anchor_id for anchor in grace_map.anchors}
    all_module_ids = {module.module_id for module in grace_map.modules}
    queried_anchor_ids = {anchor.anchor_id for anchor in QUERY.query_anchors(grace_map)}
    queried_module_ids = {module.module_id for module in QUERY.query_modules(grace_map)}

    assert queried_anchor_ids == all_anchor_ids
    assert queried_module_ids == all_module_ids
