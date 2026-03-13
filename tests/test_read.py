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
def load_read_modules():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.map",
        "grace.query",
        "grace.read",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "map", "query", "read"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["models"], loaded["parser"], loaded["map"], loaded["query"], loaded["read"]


MODELS, PARSER, MAP, QUERY, READ = load_read_modules()


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
    repo_dir = tmp_path.parent / f"{tmp_path.name}_read_files"
    repo_dir.mkdir(parents=True, exist_ok=True)
    path = repo_dir / name
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return PARSER.parse_python_file(path)


def build_read_state(tmp_path: Path):
    pricing = parse_file(
        tmp_path,
        make_file(
            module_header(module_id="billing.pricing", interfaces="choose_discount_strategy(customer_tier:str) -> int"),
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
            module_header(module_id="billing.audit", interfaces="record_tax() -> None"),
            function_block(
                anchor="billing.audit.record_tax",
                signature="def record_tax() -> None:",
                body="    return None",
            ),
        ),
        name="audit.py",
    )
    grace_files = (audit, pricing, tax)
    grace_map = MAP.build_project_map(grace_files)
    return grace_files, grace_map


def test_read_anchor_context_returns_existing_anchor(tmp_path: Path) -> None:
    grace_files, grace_map = build_read_state(tmp_path)

    context = READ.read_anchor_context(grace_files, grace_map, "billing.pricing.choose_discount_strategy")

    assert context.anchor_id == "billing.pricing.choose_discount_strategy"
    assert context.module_id == "billing.pricing"
    assert context.file_path.endswith("pricing.py")
    assert context.line_start == 7
    assert context.line_end == 12


def test_read_anchor_context_includes_block_annotations_and_code(tmp_path: Path) -> None:
    grace_files, grace_map = build_read_state(tmp_path)

    context = READ.read_anchor_context(grace_files, grace_map, "billing.pricing.choose_discount_strategy")

    assert context.annotations == (
        "# @grace.anchor billing.pricing.choose_discount_strategy",
        "# @grace.complexity 6",
        "# @grace.belief Pricing thresholds remain deterministic for the project baseline.",
        "# @grace.links billing.tax.apply_tax",
    )
    assert "def choose_discount_strategy(customer_tier: str) -> int:" in context.code


def test_read_anchor_context_includes_links_and_neighbors(tmp_path: Path) -> None:
    grace_files, grace_map = build_read_state(tmp_path)

    context = READ.read_anchor_context(grace_files, grace_map, "billing.tax.apply_tax")

    assert context.links == ("billing.audit.record_tax",)
    assert [anchor.anchor_id for anchor in context.neighbors] == [
        "billing.audit.record_tax",
        "billing.pricing.choose_discount_strategy",
    ]


def test_read_anchor_context_is_deterministic(tmp_path: Path) -> None:
    grace_files, grace_map = build_read_state(tmp_path)

    first = READ.read_anchor_context(grace_files, grace_map, "billing.tax.apply_tax")
    second = READ.read_anchor_context(grace_files, grace_map, "billing.tax.apply_tax")

    assert first.model_dump(mode="python") == second.model_dump(mode="python")


def test_read_anchor_context_model_dump_has_json_friendly_shape(tmp_path: Path) -> None:
    grace_files, grace_map = build_read_state(tmp_path)

    payload = READ.read_anchor_context(grace_files, grace_map, "billing.tax.apply_tax").model_dump(mode="json")

    assert payload["anchor_id"] == "billing.tax.apply_tax"
    assert payload["line_start"] == 7
    assert payload["line_end"] == 11
    assert payload["annotations"] == [
        "# @grace.anchor billing.tax.apply_tax",
        "# @grace.complexity 1",
        "# @grace.links billing.audit.record_tax",
    ]
    assert payload["code"] == "def apply_tax(amount: int) -> int:\n    return amount\n"
    assert payload["links"] == ["billing.audit.record_tax"]
    assert [anchor["anchor_id"] for anchor in payload["neighbors"]] == [
        "billing.audit.record_tax",
        "billing.pricing.choose_discount_strategy",
    ]


def test_read_anchor_context_raises_for_unknown_anchor(tmp_path: Path) -> None:
    grace_files, grace_map = build_read_state(tmp_path)

    with pytest.raises(READ.ReadLookupError):
        READ.read_anchor_context(grace_files, grace_map, "billing.unknown.anchor")
