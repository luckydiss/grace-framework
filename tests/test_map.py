from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
import types
from functools import lru_cache
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_foundation_modules():
    for module_name in ("grace", "grace.models", "grace.parser", "grace.language_adapter", "grace.python_adapter", "grace.map"):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "map"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["models"], loaded["parser"], loaded["map"]


MODELS, PARSER, MAP = load_foundation_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER, MAP
    load_foundation_modules.cache_clear()
    MODELS, PARSER, MAP = load_foundation_modules()


def write_temp_python_file(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_map_files"
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


def parse_file(tmp_path: Path, content: str, name: str = "sample.py"):
    path = write_temp_python_file(tmp_path, content, name=name)
    return PARSER.parse_python_file(path)


def test_build_file_map_for_valid_file(tmp_path: Path) -> None:
    grace_file = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount"),
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="VIP tier is the dominant pricing signal and threshold rules remain deterministic for the MVP.",
                links="billing.pricing.apply_discount",
                signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
                body="    return 0",
            ),
        ),
    )

    grace_map = MAP.build_file_map(grace_file)

    assert grace_map.grace_version == "v1"
    assert len(grace_map.modules) == 1
    assert len(grace_map.anchors) == 2


def test_build_project_map_for_two_files(tmp_path: Path) -> None:
    file_a = parse_file(tmp_path, make_file(function_block(anchor="billing.pricing.apply_discount")), name="pricing.py")
    file_b = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.tax.apply_tax", signature="def apply_tax(amount: int) -> int:", body="    return amount"),
            header=module_header(module_id="billing.tax"),
        ),
        name="tax.py",
    )

    grace_map = MAP.build_project_map([file_a, file_b])

    assert len(grace_map.modules) == 2
    assert len(grace_map.anchors) == 2


def test_project_map_builds_cross_file_link_edges(tmp_path: Path) -> None:
    file_a = parse_file(
        tmp_path,
        make_file(
            function_block(
                anchor="billing.pricing.apply_discount",
                complexity="6",
                belief="Pricing thresholds remain deterministic for the project baseline.",
                links="billing.tax.apply_tax",
            )
        ),
        name="pricing.py",
    )
    file_b = parse_file(
        tmp_path,
        make_file(
            function_block(
                anchor="billing.tax.apply_tax",
                signature="def apply_tax(amount: int) -> int:",
                body="    return amount",
            ),
            header=module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
        ),
        name="tax.py",
    )

    grace_map = MAP.build_project_map([file_a, file_b])
    link_edges = [edge for edge in grace_map.edges if edge.type == "anchor_links_to_anchor"]

    assert len(link_edges) == 1
    assert link_edges[0].source == "billing.pricing.apply_discount"
    assert link_edges[0].target == "billing.tax.apply_tax"


def test_map_does_not_introduce_new_identity(tmp_path: Path) -> None:
    grace_file = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount"),
            function_block(anchor="billing.pricing.compute_discount", signature="def compute_discount() -> int:", body="    return 0"),
        ),
    )

    grace_map = MAP.build_file_map(grace_file)

    module_ids = {module.module_id for module in grace_map.modules}
    anchor_ids = {anchor.anchor_id for anchor in grace_map.anchors}

    assert module_ids == {grace_file.module.module_id}
    assert anchor_ids == {block.anchor_id for block in grace_file.blocks}


def test_links_are_converted_to_edges(tmp_path: Path) -> None:
    grace_file = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount"),
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="VIP tier is the dominant pricing signal and threshold rules remain deterministic for the MVP.",
                links="billing.pricing.apply_discount",
                signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
                body="    return 0",
            ),
        ),
    )

    grace_map = MAP.build_file_map(grace_file)
    link_edges = [edge for edge in grace_map.edges if edge.type == "anchor_links_to_anchor"]

    assert len(link_edges) == 1
    assert link_edges[0].source == "billing.pricing.choose_discount_strategy"
    assert link_edges[0].target == "billing.pricing.apply_discount"


def test_module_has_anchor_edges_are_built_correctly(tmp_path: Path) -> None:
    grace_file = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount"),
            function_block(anchor="billing.pricing.compute_discount", signature="def compute_discount() -> int:", body="    return 0"),
        ),
    )

    grace_map = MAP.build_file_map(grace_file)
    module_edges = [edge for edge in grace_map.edges if edge.type == "module_has_anchor"]

    assert len(module_edges) == 2
    assert {edge.source for edge in module_edges} == {"billing.pricing"}
    assert {edge.target for edge in module_edges} == {
        "billing.pricing.apply_discount",
        "billing.pricing.compute_discount",
    }


def test_map_serializes_to_json_friendly_dict_shape(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block()))
    grace_map = MAP.build_file_map(grace_file)

    payload = MAP.map_to_dict(grace_map)
    encoded = json.dumps(payload)

    assert isinstance(payload, dict)
    assert "modules" in payload
    assert "anchors" in payload
    assert "edges" in payload
    assert isinstance(payload["modules"], list)
    assert isinstance(payload["anchors"], list)
    assert isinstance(payload["edges"], list)
    assert isinstance(encoded, str)


def test_map_builder_does_not_reparse_source_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block()))

    def _boom(*args, **kwargs):
        raise AssertionError("map builder must not call parser")

    monkeypatch.setattr(PARSER, "parse_python_file", _boom)

    grace_map = MAP.build_file_map(grace_file)

    assert grace_map.modules[0].module_id == grace_file.module.module_id


def test_project_map_is_deterministic_across_repeated_builds(tmp_path: Path) -> None:
    file_a = parse_file(tmp_path, make_file(function_block(anchor="billing.pricing.apply_discount")), name="pricing.py")
    file_b = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.tax.apply_tax", signature="def apply_tax(amount: int) -> int:", body="    return amount"),
            header=module_header(module_id="billing.tax"),
        ),
        name="tax.py",
    )

    first = MAP.build_project_map([file_b, file_a])
    second = MAP.build_project_map([file_a, file_b])

    assert first.model_dump(mode="python") == second.model_dump(mode="python")
