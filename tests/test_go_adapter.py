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
        "grace.go_adapter",
        "grace.validator",
        "grace.linter",
        "grace.map",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in (
        "models",
        "parser",
        "language_adapter",
        "python_adapter",
        "go_adapter",
        "validator",
        "linter",
        "map",
    ):
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
        loaded["go_adapter"],
        loaded["validator"],
        loaded["linter"],
        loaded["map"],
    )


MODELS, PARSER, LANGUAGE_ADAPTER, GO_ADAPTER, VALIDATOR, LINTER, MAP = load_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER, LANGUAGE_ADAPTER, GO_ADAPTER, VALIDATOR, LINTER, MAP
    load_modules.cache_clear()
    MODELS, PARSER, LANGUAGE_ADAPTER, GO_ADAPTER, VALIDATOR, LINTER, MAP = load_modules()


def write_temp_go_file(tmp_path: Path, content: str, name: str = "sample.go") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_go_adapter_files"
    writable_dir.mkdir(parents=True, exist_ok=True)
    path = writable_dir / name
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def module_header() -> str:
    return (
        "// @grace.module billing.pricing\n"
        "// @grace.purpose Determine pricing behavior in Go.\n"
        "// @grace.interfaces apply_discount(price int, percent int) int; billingService.run() int\n"
        "// @grace.invariant Discount percent must never be negative.\n"
        "// @grace.invariant Anchor ids remain stable unless pricing semantics change.\n"
    )


def make_file(*sections: str, header: str | None = None) -> str:
    active_header = header if header is not None else module_header()
    body = "\n\n".join(section.strip("\n") for section in sections)
    return f"{active_header.rstrip()}\n\n{body}\n"


def test_language_adapter_registry_returns_go_adapter_for_go_path(tmp_path: Path) -> None:
    path = write_temp_go_file(
        tmp_path,
        make_file(
            """
            // @grace.anchor billing.pricing.apply_discount
            // @grace.complexity 1
            func apply_discount(price int, percent int) int {
                return price - ((price * percent) / 100)
            }
            """
        ),
    )

    adapter = LANGUAGE_ADAPTER.get_language_adapter_for_path(path)

    assert isinstance(adapter, GO_ADAPTER.GoAdapter)
    assert adapter.language_name == "go"


def test_go_adapter_parses_module_header_function_type_and_method(tmp_path: Path) -> None:
    path = write_temp_go_file(
        tmp_path,
        make_file(
            """
            // @grace.anchor billing.pricing.apply_discount
            // @grace.complexity 1
            func apply_discount(price int, percent int) int {
                return price - ((price * percent) / 100)
            }
            """,
            """
            // @grace.anchor billing.pricing.load_discount
            // @grace.complexity 6
            // @grace.belief Go pilot keeps higher-complexity fixtures deterministic so adapter tests exercise only binding and spans.
            // @grace.links billing.pricing.apply_discount
            func load_discount() int {
                return apply_discount(100, 10)
            }
            """,
            """
            // @grace.anchor billing.pricing.BillingService
            // @grace.complexity 2
            type BillingService struct {
            }

            // @grace.anchor billing.pricing.BillingService.run
            // @grace.complexity 1
            // @grace.links billing.pricing.apply_discount
            func (service BillingService) run() int {
                return apply_discount(100, 10)
            }
            """,
        ),
    )

    grace_file = PARSER.parse_python_file(path)

    assert grace_file.module.module_id == "billing.pricing"
    assert tuple(block.anchor_id for block in grace_file.blocks) == (
        "billing.pricing.apply_discount",
        "billing.pricing.load_discount",
        "billing.pricing.BillingService",
        "billing.pricing.BillingService.run",
    )
    assert grace_file.blocks[0].kind is MODELS.BlockKind.FUNCTION
    assert grace_file.blocks[1].kind is MODELS.BlockKind.FUNCTION
    assert grace_file.blocks[2].kind is MODELS.BlockKind.CLASS
    assert grace_file.blocks[3].kind is MODELS.BlockKind.METHOD
    assert grace_file.blocks[3].qualified_name == "BillingService.run"


def test_go_adapter_produces_deterministic_output(tmp_path: Path) -> None:
    path = write_temp_go_file(
        tmp_path,
        make_file(
            """
            // @grace.anchor billing.pricing.apply_discount
            // @grace.complexity 1
            func apply_discount(price int, percent int) int {
                return price - ((price * percent) / 100)
            }
            """
        ),
    )

    first = PARSER.parse_python_file(path)
    second = PARSER.parse_python_file(path)

    assert first.model_dump(mode="python") == second.model_dump(mode="python")


def test_core_layers_accept_go_adapter_output(tmp_path: Path) -> None:
    path = write_temp_go_file(
        tmp_path,
        make_file(
            """
            // @grace.anchor billing.pricing.apply_discount
            // @grace.complexity 1
            func apply_discount(price int, percent int) int {
                return price - ((price * percent) / 100)
            }
            """,
            """
            // @grace.anchor billing.pricing.BillingService
            // @grace.complexity 2
            type BillingService struct {
            }
            """,
            """
            // @grace.anchor billing.pricing.BillingService.run
            // @grace.complexity 1
            // @grace.links billing.pricing.apply_discount
            func (service BillingService) run() int {
                return apply_discount(100, 10)
            }
            """,
        ),
    )

    grace_file = PARSER.parse_python_file(path)
    validation_result = VALIDATOR.validate_file(grace_file)
    lint_result = LINTER.lint_file(grace_file)
    grace_map = MAP.build_file_map(grace_file)

    assert isinstance(validation_result, VALIDATOR.ValidationSuccess)
    assert lint_result.ok is True
    assert grace_map.modules[0].module_id == "billing.pricing"
    assert tuple(anchor.anchor_id for anchor in grace_map.anchors) == (
        "billing.pricing.BillingService",
        "billing.pricing.BillingService.run",
        "billing.pricing.apply_discount",
    )


def test_go_adapter_rejects_invalid_binding_target(tmp_path: Path) -> None:
    path = write_temp_go_file(
        tmp_path,
        make_file(
            """
            // @grace.anchor billing.pricing.Unsupported
            // @grace.complexity 1
            type Unsupported interface {
                Run() int
            }
            """
        ),
    )

    with pytest.raises(PARSER.GraceParseError) as exc_info:
        PARSER.parse_python_file(path)

    assert any(
        issue.code is MODELS.ParseErrorCode.ARBITRARY_CODE_BETWEEN_ANNOTATIONS_AND_BLOCK
        for issue in exc_info.value.errors
    )
