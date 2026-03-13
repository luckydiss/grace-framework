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
        "grace.tree_sitter_adapter",
        "grace.typescript_adapter",
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
        "tree_sitter_adapter",
        "typescript_adapter",
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
        loaded["typescript_adapter"],
        loaded["validator"],
        loaded["linter"],
        loaded["map"],
    )


MODELS, PARSER, LANGUAGE_ADAPTER, TYPESCRIPT_ADAPTER, VALIDATOR, LINTER, MAP = load_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER, LANGUAGE_ADAPTER, TYPESCRIPT_ADAPTER, VALIDATOR, LINTER, MAP
    load_modules.cache_clear()
    MODELS, PARSER, LANGUAGE_ADAPTER, TYPESCRIPT_ADAPTER, VALIDATOR, LINTER, MAP = load_modules()


def write_temp_ts_file(tmp_path: Path, content: str, name: str = "sample.ts") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_typescript_adapter_files"
    writable_dir.mkdir(parents=True, exist_ok=True)
    path = writable_dir / name
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def module_header() -> str:
    return (
        "// @grace.module billing.pricing\n"
        "// @grace.purpose Determine pricing behavior in TypeScript.\n"
        "// @grace.interfaces applyDiscount(price:number, percent:number): number; chooseDiscount(customerTier:string): Promise<number>\n"
        "// @grace.invariant Discount percent must never be negative.\n"
        "// @grace.invariant Anchor ids remain stable unless pricing semantics change.\n"
    )


def make_file(*sections: str, header: str | None = None) -> str:
    active_header = header if header is not None else module_header()
    body = "\n\n".join(section.strip("\n") for section in sections)
    return f"{active_header.rstrip()}\n\n{body}\n"


def test_language_adapter_registry_returns_typescript_adapter_for_ts_path(tmp_path: Path) -> None:
    path = write_temp_ts_file(
        tmp_path,
        make_file(
            """
            // @grace.anchor billing.pricing.applyDiscount
            // @grace.complexity 1
            function applyDiscount(price: number, percent: number): number {
              return price - Math.floor((price * percent) / 100);
            }
            """
        ),
    )

    adapter = LANGUAGE_ADAPTER.get_language_adapter_for_path(path)

    assert isinstance(adapter, TYPESCRIPT_ADAPTER.TypeScriptAdapter)
    assert adapter.language_name == "typescript"


def test_typescript_adapter_parses_module_header_and_supported_blocks(tmp_path: Path) -> None:
    path = write_temp_ts_file(
        tmp_path,
        make_file(
            """
            // @grace.anchor billing.pricing.applyDiscount
            // @grace.complexity 1
            function applyDiscount(price: number, percent: number): number {
              return price - Math.floor((price * percent) / 100);
            }
            """,
            """
            /* @grace.anchor billing.pricing.chooseDiscount */
            /* @grace.complexity 6 */
            /* @grace.belief VIP remains the dominant signal in the TypeScript pilot adapter. */
            /* @grace.links billing.pricing.applyDiscount */
            async function chooseDiscount(customerTier: string): Promise<number> {
              return customerTier === "vip" ? 15 : 0;
            }
            """,
            """
            // @grace.anchor billing.pricing.StrategyRegistry
            // @grace.complexity 2
            class StrategyRegistry {
              // @grace.anchor billing.pricing.StrategyRegistry.resolve
              // @grace.complexity 1
              resolve(): number {
                return 0;
              }
            }
            """,
        ),
    )

    grace_file = PARSER.parse_python_file(path)

    assert grace_file.module.module_id == "billing.pricing"
    assert tuple(block.anchor_id for block in grace_file.blocks) == (
        "billing.pricing.applyDiscount",
        "billing.pricing.chooseDiscount",
        "billing.pricing.StrategyRegistry",
        "billing.pricing.StrategyRegistry.resolve",
    )
    assert grace_file.blocks[0].kind is MODELS.BlockKind.FUNCTION
    assert grace_file.blocks[1].kind is MODELS.BlockKind.ASYNC_FUNCTION
    assert grace_file.blocks[2].kind is MODELS.BlockKind.CLASS
    assert grace_file.blocks[3].kind is MODELS.BlockKind.METHOD
    assert grace_file.blocks[3].qualified_name == "StrategyRegistry.resolve"


def test_typescript_adapter_produces_deterministic_output(tmp_path: Path) -> None:
    path = write_temp_ts_file(
        tmp_path,
        make_file(
            """
            // @grace.anchor billing.pricing.applyDiscount
            // @grace.complexity 1
            function applyDiscount(price: number, percent: number): number {
              return price - Math.floor((price * percent) / 100);
            }
            """
        ),
    )

    first = PARSER.parse_python_file(path)
    second = PARSER.parse_python_file(path)

    assert first.model_dump(mode="python") == second.model_dump(mode="python")


def test_core_layers_accept_typescript_adapter_output(tmp_path: Path) -> None:
    path = write_temp_ts_file(
        tmp_path,
        make_file(
            """
            // @grace.anchor billing.pricing.applyDiscount
            // @grace.complexity 1
            function applyDiscount(price: number, percent: number): number {
              return price - Math.floor((price * percent) / 100);
            }
            """,
            """
            /* @grace.anchor billing.pricing.chooseDiscount */
            /* @grace.complexity 6 */
            /* @grace.belief VIP remains the dominant signal in the TypeScript pilot adapter. */
            /* @grace.links billing.pricing.applyDiscount */
            async function chooseDiscount(customerTier: string): Promise<number> {
              return customerTier === "vip" ? 15 : 0;
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
        "billing.pricing.applyDiscount",
        "billing.pricing.chooseDiscount",
    )


def test_typescript_adapter_rejects_invalid_binding_target(tmp_path: Path) -> None:
    path = write_temp_ts_file(
        tmp_path,
        make_file(
            """
            // @grace.anchor billing.pricing.applyDiscount
            // @grace.complexity 1
            const applyDiscount = (price: number, percent: number): number => {
              return price - Math.floor((price * percent) / 100);
            };
            """
        ),
    )

    with pytest.raises(PARSER.GraceParseError) as exc_info:
        PARSER.parse_python_file(path)

    assert any(
        issue.code is MODELS.ParseErrorCode.ARBITRARY_CODE_BETWEEN_ANNOTATIONS_AND_BLOCK
        for issue in exc_info.value.errors
    )
