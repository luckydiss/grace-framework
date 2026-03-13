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
def load_modules():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.language_adapter",
        "grace.python_adapter",
        "grace.validator",
        "grace.linter",
        "grace.map",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "language_adapter", "python_adapter", "validator", "linter", "map"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return (
        loaded["models"],
        loaded["parser"],
        loaded["language_adapter"],
        loaded["python_adapter"],
        loaded["validator"],
        loaded["linter"],
        loaded["map"],
    )


MODELS, PARSER, LANGUAGE_ADAPTER, PYTHON_ADAPTER, VALIDATOR, LINTER, MAP = load_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER, LANGUAGE_ADAPTER, PYTHON_ADAPTER, VALIDATOR, LINTER, MAP
    load_modules.cache_clear()
    MODELS, PARSER, LANGUAGE_ADAPTER, PYTHON_ADAPTER, VALIDATOR, LINTER, MAP = load_modules()


def write_temp_python_file(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_language_adapter_files"
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


def test_language_adapter_registry_returns_python_adapter_for_py_path(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")

    adapter = LANGUAGE_ADAPTER.get_language_adapter_for_path(path)

    assert isinstance(adapter, PYTHON_ADAPTER.PythonAdapter)
    assert adapter.language_name == "python"


def test_python_adapter_produces_same_grace_file_model_as_parser_entrypoint(tmp_path: Path) -> None:
    path = write_temp_python_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount"),
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="Pricing thresholds remain deterministic for the adapter baseline.",
                links="billing.pricing.apply_discount",
                signature="def choose_discount_strategy(customer_tier: str) -> int:",
                body="    return 0",
            ),
        ),
        name="pricing.py",
    )

    adapter = PYTHON_ADAPTER.PythonAdapter()
    parsed_via_entrypoint = PARSER.parse_python_file(path)
    parsed_via_adapter = adapter.build_grace_file_model(path)

    assert parsed_via_entrypoint.model_dump(mode="python") == parsed_via_adapter.model_dump(mode="python")


def test_core_layers_continue_to_work_with_adapter_backed_parser(tmp_path: Path) -> None:
    path = write_temp_python_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount"),
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="Pricing thresholds remain deterministic for the adapter baseline.",
                links="billing.pricing.apply_discount",
                signature="def choose_discount_strategy(customer_tier: str) -> int:",
                body="    return 0",
            ),
        ),
        name="pricing.py",
    )

    grace_file = PARSER.parse_python_file(path)
    validation_result = VALIDATOR.validate_file(grace_file)
    lint_result = LINTER.lint_file(grace_file)
    grace_map = MAP.build_file_map(grace_file)

    assert isinstance(validation_result, VALIDATOR.ValidationSuccess)
    assert grace_map.modules[0].module_id == "billing.pricing"
    assert grace_map.anchors[0].module_id == "billing.pricing"
    assert lint_result.ok is True
