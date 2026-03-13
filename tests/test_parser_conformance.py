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
def load_foundation_modules():
    for module_name in ("grace", "grace.models", "grace.parser", "grace.language_adapter", "grace.python_adapter"):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    models_spec = importlib.util.spec_from_file_location("grace.models", ROOT / "grace" / "models.py")
    assert models_spec is not None and models_spec.loader is not None
    models_module = importlib.util.module_from_spec(models_spec)
    sys.modules["grace.models"] = models_module
    models_spec.loader.exec_module(models_module)

    parser_spec = importlib.util.spec_from_file_location("grace.parser", ROOT / "grace" / "parser.py")
    assert parser_spec is not None and parser_spec.loader is not None
    parser_module = importlib.util.module_from_spec(parser_spec)
    sys.modules["grace.parser"] = parser_module
    parser_spec.loader.exec_module(parser_module)

    return models_module, parser_module


MODELS, PARSER = load_foundation_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER
    load_foundation_modules.cache_clear()
    MODELS, PARSER = load_foundation_modules()


def write_temp_python_file(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_files"
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


def make_file(*sections: str, header: str | None = None) -> str:
    active_header = header if header is not None else module_header()
    body = "\n\n".join(section.strip("\n") for section in sections)
    return f"{active_header.rstrip()}\n\n{body}\n"


def parse_success(tmp_path: Path, content: str, name: str = "sample.py"):
    path = write_temp_python_file(tmp_path, content, name=name)
    parsed = PARSER.parse_python_file(path)
    assert isinstance(parsed, MODELS.GraceFileModel)
    return parsed


def parse_failure(tmp_path: Path, content: str, name: str = "sample.py"):
    path = write_temp_python_file(tmp_path, content, name=name)
    with pytest.raises(PARSER.GraceParseError) as exc_info:
        PARSER.parse_python_file(path)
    return exc_info.value, path


def assert_failure_result(tmp_path: Path, content: str, name: str = "sample.py"):
    _, path = parse_failure(tmp_path, content, name=name)
    result = PARSER.try_parse_python_file(path)
    assert isinstance(result, MODELS.GraceParseFailure)
    assert result.ok is False
    assert result.path == path
    assert result.errors
    return result


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


def class_block(
    *,
    anchor: str = "billing.pricing.DiscountPolicy",
    complexity: str = "1",
    belief: str | None = None,
    links: str | None = None,
    class_name: str = "DiscountPolicy",
    body: str = "    pass",
) -> str:
    lines = [
        f"# @grace.anchor {anchor}",
        f"# @grace.complexity {complexity}",
    ]
    if belief is not None:
        lines.append(f"# @grace.belief {belief}")
    if links is not None:
        lines.append(f"# @grace.links {links}")
    lines.extend([f"class {class_name}:", body])
    return "\n".join(lines)


def error_codes(parse_error) -> set[str]:
    return {issue.code.value for issue in parse_error.errors}


# Spec-level parser requirements start here.
def test_module_header_parses_required_annotations(tmp_path: Path) -> None:
    parsed = parse_success(
        tmp_path,
        make_file(
            function_block(),
            header=module_header(
                purpose="Determine pricing behavior for discounts.",
                interfaces="apply_discount(price:int, percent:int) -> int",
                invariants=(
                    "Discount percent must never be negative.",
                    "Anchor ids are stable unless semantics change.",
                ),
            ),
        ),
    )

    assert parsed.module.module_id == "billing.pricing"
    assert parsed.module.purpose == "Determine pricing behavior for discounts."
    assert parsed.module.interfaces == "apply_discount(price:int, percent:int) -> int"
    assert parsed.module.invariants == (
        "Discount percent must never be negative.",
        "Anchor ids are stable unless semantics change.",
    )


@pytest.mark.parametrize(
    ("description", "header"),
    [
        (
            "duplicate module",
            (
                "# @grace.module billing.pricing\n"
                "# @grace.module billing.tax\n"
                "# @grace.purpose Determine pricing behavior.\n"
                "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
                "# @grace.invariant Discount percent must never be negative.\n"
            ),
        ),
        (
            "duplicate purpose",
            (
                "# @grace.module billing.pricing\n"
                "# @grace.purpose Determine pricing behavior.\n"
                "# @grace.purpose Alternate text.\n"
                "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
                "# @grace.invariant Discount percent must never be negative.\n"
            ),
        ),
        (
            "duplicate interfaces",
            (
                "# @grace.module billing.pricing\n"
                "# @grace.purpose Determine pricing behavior.\n"
                "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
                "# @grace.interfaces choose_discount_strategy(customer_tier:str, cart_total:int) -> int\n"
                "# @grace.invariant Discount percent must never be negative.\n"
            ),
        ),
        (
            "missing module",
            (
                "# @grace.purpose Determine pricing behavior.\n"
                "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
                "# @grace.invariant Discount percent must never be negative.\n"
            ),
        ),
        (
            "missing purpose",
            (
                "# @grace.module billing.pricing\n"
                "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
                "# @grace.invariant Discount percent must never be negative.\n"
            ),
        ),
        (
            "missing interfaces",
            (
                "# @grace.module billing.pricing\n"
                "# @grace.purpose Determine pricing behavior.\n"
                "# @grace.invariant Discount percent must never be negative.\n"
            ),
        ),
        (
            "missing invariant",
            (
                "# @grace.module billing.pricing\n"
                "# @grace.purpose Determine pricing behavior.\n"
                "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
            ),
        ),
    ],
)
def test_module_header_hard_errors_for_missing_or_duplicate_required_annotations(
    tmp_path: Path, description: str, header: str
) -> None:
    error, _ = parse_failure(tmp_path, make_file(function_block(), header=header), name=f"{description}.py")
    assert error.errors


@pytest.mark.parametrize(
    ("description", "header", "expected_code"),
    [
        (
            "empty purpose",
            (
                "# @grace.module billing.pricing\n"
                "# @grace.purpose\n"
                "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
                "# @grace.invariant Discount percent must never be negative.\n"
            ),
            "empty_annotation_payload",
        ),
        (
            "empty interfaces",
            (
                "# @grace.module billing.pricing\n"
                "# @grace.purpose Determine pricing behavior.\n"
                "# @grace.interfaces\n"
                "# @grace.invariant Discount percent must never be negative.\n"
            ),
            "empty_annotation_payload",
        ),
        (
            "empty invariant",
            (
                "# @grace.module billing.pricing\n"
                "# @grace.purpose Determine pricing behavior.\n"
                "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
                "# @grace.invariant\n"
            ),
            "empty_annotation_payload",
        ),
    ],
)
def test_module_header_empty_payloads_are_hard_errors(
    tmp_path: Path, description: str, header: str, expected_code: str
) -> None:
    error, _ = parse_failure(tmp_path, make_file(function_block(), header=header), name=f"{description}.py")
    assert expected_code in error_codes(error)


def test_module_header_rejects_invariant_after_first_block_header(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 1\n"
            "# @grace.invariant Discount percent must never be negative.\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    error, _ = parse_failure(tmp_path, content)
    assert "module_annotation_after_blocks" in error_codes(error)


def test_spec_parser_rejects_module_annotation_after_block_declarations_even_if_duplicate(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 1\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)\n\n"
            "# @grace.module billing.pricing.duplicate"
        )
    )

    error, _ = parse_failure(tmp_path, content)
    assert "module_annotation_after_blocks" in error_codes(error)


def test_block_annotations_bind_to_nearest_def(tmp_path: Path) -> None:
    parsed = parse_success(tmp_path, make_file(function_block()))
    assert parsed.blocks[0].kind is MODELS.BlockKind.FUNCTION
    assert parsed.blocks[0].symbol_name == "apply_discount"


def test_block_annotations_bind_to_nearest_async_def(tmp_path: Path) -> None:
    parsed = parse_success(
        tmp_path,
        make_file(
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                signature="async def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
                body="    return 0",
            )
        ),
    )

    assert parsed.blocks[0].kind is MODELS.BlockKind.ASYNC_FUNCTION
    assert parsed.blocks[0].is_async is True


def test_block_annotations_bind_to_nearest_class(tmp_path: Path) -> None:
    parsed = parse_success(tmp_path, make_file(class_block()))
    assert parsed.blocks[0].kind is MODELS.BlockKind.CLASS
    assert parsed.blocks[0].symbol_name == "DiscountPolicy"


def test_block_annotations_bind_to_method_inside_class(tmp_path: Path) -> None:
    content = make_file(
        (
            "class DiscountPolicy:\n"
            "    # @grace.anchor billing.pricing.DiscountPolicy.choose_discount_strategy\n"
            "    # @grace.complexity 1\n"
            "    def choose_discount_strategy(self, customer_tier: str) -> int:\n"
            "        return 0"
        )
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[0].kind is MODELS.BlockKind.METHOD
    assert parsed.blocks[0].qualified_name == "DiscountPolicy.choose_discount_strategy"


def test_block_annotations_without_following_definition_are_hard_error(tmp_path: Path) -> None:
    error, _ = parse_failure(
        tmp_path,
        make_file("# @grace.anchor billing.pricing.apply_discount\n# @grace.complexity 1"),
    )
    assert "orphan_block_annotations" in error_codes(error)


def test_arbitrary_code_between_annotations_and_target_block_is_hard_error(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 1\n"
            "x = 1\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    error, _ = parse_failure(tmp_path, content)
    assert "arbitrary_code_between_annotations_and_block" in error_codes(error)


def test_spec_parser_allows_blank_lines_between_block_annotations_and_target(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n\n"
            "# @grace.complexity 1\n\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[0].anchor_id == "billing.pricing.apply_discount"


def test_current_parser_contract_allows_non_grace_comments_between_block_annotations_and_target(tmp_path: Path) -> None:
    # This is current parser behavior, not a separate v1 semantic guarantee.
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 1\n"
            "# regular comment retained between annotations and target\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[0].symbol_name == "apply_discount"


def test_decorated_def_after_annotations_parses_successfully(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 1\n"
            "@staticmethod\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[0].kind is MODELS.BlockKind.FUNCTION


def test_multiple_decorators_between_annotations_and_def_parse_successfully(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 1\n"
            "@cache\n"
            "@trace\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[0].symbol_name == "apply_discount"


def test_decorator_then_async_def_parses_successfully(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.choose_discount_strategy\n"
            "# @grace.complexity 1\n"
            "@trace\n"
            "async def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:\n"
            "    return 0"
        )
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[0].kind is MODELS.BlockKind.ASYNC_FUNCTION


def test_current_parser_contract_supports_decorator_then_class(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.DiscountPolicy\n"
            "# @grace.complexity 1\n"
            "@dataclass\n"
            "class DiscountPolicy:\n"
            "    pass"
        )
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[0].kind is MODELS.BlockKind.CLASS


@pytest.mark.parametrize("complexity", ["1", "5"])
def test_complexity_below_threshold_does_not_require_belief(tmp_path: Path, complexity: str) -> None:
    parsed = parse_success(tmp_path, make_file(function_block(complexity=complexity)))
    assert parsed.blocks[0].complexity == int(complexity)
    assert parsed.blocks[0].belief is None


@pytest.mark.parametrize("complexity", ["6", "7", "10"])
def test_complexity_at_or_above_threshold_requires_belief(tmp_path: Path, complexity: str) -> None:
    error, _ = parse_failure(tmp_path, make_file(function_block(complexity=complexity)))
    assert "missing_required_belief" in error_codes(error)


def test_complexity_six_with_belief_parses_successfully(tmp_path: Path) -> None:
    parsed = parse_success(
        tmp_path,
        make_file(
            function_block(
                complexity="6",
                belief="Threshold pricing is deterministic for the MVP.",
            )
        ),
    )

    assert parsed.blocks[0].belief == "Threshold pricing is deterministic for the MVP."


def test_spec_parser_rejects_empty_belief_payload_at_or_above_threshold(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 6\n"
            "# @grace.belief\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    error, _ = parse_failure(tmp_path, content)
    codes = error_codes(error)
    assert "empty_annotation_payload" in codes
    assert "missing_required_belief" in codes


@pytest.mark.parametrize("complexity", ["0", "11", "0.7", "high"])
def test_invalid_complexity_values_are_hard_errors(tmp_path: Path, complexity: str) -> None:
    error, _ = parse_failure(tmp_path, make_file(function_block(complexity=complexity)))
    assert "invalid_complexity" in error_codes(error)


def test_single_valid_link_parses_successfully(tmp_path: Path) -> None:
    content = make_file(
        function_block(anchor="billing.pricing.apply_discount", complexity="1"),
        function_block(
            anchor="billing.pricing.choose_discount_strategy",
            complexity="6",
            belief="Threshold pricing is deterministic for the MVP.",
            links="billing.pricing.apply_discount",
            signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
            body="    return 0",
        ),
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[1].links == ("billing.pricing.apply_discount",)


def test_multiple_valid_links_parse_successfully(tmp_path: Path) -> None:
    content = make_file(
        function_block(anchor="billing.pricing.apply_discount", complexity="1"),
        function_block(
            anchor="billing.pricing.compute_base_discount",
            complexity="1",
            signature="def compute_base_discount() -> int:",
            body="    return 0",
        ),
        function_block(
            anchor="billing.pricing.choose_discount_strategy",
            complexity="6",
            belief="Threshold pricing is deterministic for the MVP.",
            links="billing.pricing.apply_discount,billing.pricing.compute_base_discount",
            signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
            body="    return 0",
        ),
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[2].links == (
        "billing.pricing.apply_discount",
        "billing.pricing.compute_base_discount",
    )


def test_links_with_spaces_are_normalized_to_clean_anchor_ids(tmp_path: Path) -> None:
    content = make_file(
        function_block(anchor="billing.pricing.apply_discount", complexity="1"),
        function_block(
            anchor="billing.pricing.compute_base_discount",
            complexity="1",
            signature="def compute_base_discount() -> int:",
            body="    return 0",
        ),
        function_block(
            anchor="billing.pricing.choose_discount_strategy",
            complexity="6",
            belief="Threshold pricing is deterministic for the MVP.",
            links="billing.pricing.apply_discount, billing.pricing.compute_base_discount",
            signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
            body="    return 0",
        ),
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[2].links == (
        "billing.pricing.apply_discount",
        "billing.pricing.compute_base_discount",
    )


def test_current_parser_contract_allows_unresolved_link_target_for_deferred_project_validation(tmp_path: Path) -> None:
    content = make_file(
        function_block(
            anchor="billing.pricing.choose_discount_strategy",
            complexity="6",
            belief="Threshold pricing is deterministic for the MVP.",
            links="billing.pricing.missing_anchor",
            signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
            body="    return 0",
        )
    )

    parsed = parse_success(tmp_path, content)
    assert parsed.blocks[0].links == ("billing.pricing.missing_anchor",)


def test_empty_links_annotation_is_hard_error(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 1\n"
            "# @grace.links\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    error, _ = parse_failure(tmp_path, content)
    assert "empty_annotation_payload" in error_codes(error)


def test_duplicate_anchor_in_same_file_is_hard_error(tmp_path: Path) -> None:
    content = make_file(
        function_block(anchor="billing.pricing.apply_discount", complexity="1"),
        function_block(
            anchor="billing.pricing.apply_discount",
            complexity="1",
            signature="def apply_discount_v2(price: int, percent: int) -> int:",
            body="    return price",
        ),
    )

    error, _ = parse_failure(tmp_path, content)
    assert "duplicate_anchor_id" in error_codes(error)


def test_duplicate_anchor_between_function_and_method_is_hard_error(tmp_path: Path) -> None:
    content = make_file(
        function_block(anchor="billing.pricing.apply_discount", complexity="1"),
        (
            "class DiscountPolicy:\n"
            "    # @grace.anchor billing.pricing.apply_discount\n"
            "    # @grace.complexity 1\n"
            "    def choose_discount_strategy(self) -> int:\n"
            "        return 0"
        ),
    )

    error, _ = parse_failure(tmp_path, content)
    assert "duplicate_anchor_id" in error_codes(error)


def test_duplicate_anchor_between_class_and_method_is_hard_error(tmp_path: Path) -> None:
    content = make_file(
        class_block(anchor="billing.pricing.DiscountPolicy", complexity="1"),
        (
            "class PricingEngine:\n"
            "    # @grace.anchor billing.pricing.DiscountPolicy\n"
            "    # @grace.complexity 1\n"
            "    def run(self) -> int:\n"
            "        return 0"
        ),
    )

    error, _ = parse_failure(tmp_path, content)
    assert "duplicate_anchor_id" in error_codes(error)


def test_spec_parser_distinguishes_function_async_function_class_and_method_kinds(tmp_path: Path) -> None:
    content = make_file(
        function_block(anchor="billing.pricing.apply_discount", complexity="1"),
        function_block(
            anchor="billing.pricing.choose_discount_strategy",
            complexity="6",
            belief="Threshold pricing is deterministic for the MVP.",
            signature="async def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
            body="    return 0",
        ),
        class_block(anchor="billing.pricing.DiscountPolicy", complexity="1", body="    pass"),
        (
            "class StrategyRegistry:\n"
            "    # @grace.anchor billing.pricing.StrategyRegistry.resolve\n"
            "    # @grace.complexity 1\n"
            "    def resolve(self) -> int:\n"
            "        return 0\n\n"
            "    # @grace.anchor billing.pricing.StrategyRegistry.resolve_async\n"
            "    # @grace.complexity 6\n"
            "    # @grace.belief Async retrieval is deterministic for the MVP.\n"
            "    async def resolve_async(self) -> int:\n"
            "        return 0"
        ),
    )

    parsed = parse_success(tmp_path, content)
    kinds = {block.anchor_id: block.kind for block in parsed.blocks}

    assert kinds["billing.pricing.apply_discount"] is MODELS.BlockKind.FUNCTION
    assert kinds["billing.pricing.choose_discount_strategy"] is MODELS.BlockKind.ASYNC_FUNCTION
    assert kinds["billing.pricing.DiscountPolicy"] is MODELS.BlockKind.CLASS
    assert kinds["billing.pricing.StrategyRegistry.resolve"] is MODELS.BlockKind.METHOD

    # Current parser/model contract represents async methods as kind=method with is_async=True.
    async_method = next(block for block in parsed.blocks if block.anchor_id == "billing.pricing.StrategyRegistry.resolve_async")
    assert async_method.kind is MODELS.BlockKind.METHOD
    assert async_method.is_async is True


def test_canonical_module_annotation_order_parses_successfully(tmp_path: Path) -> None:
    parsed = parse_success(tmp_path, make_file(function_block()))
    assert parsed.module.module_id == "billing.pricing"


def test_canonical_block_annotation_order_parses_successfully(tmp_path: Path) -> None:
    parsed = parse_success(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount", complexity="1"),
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="Threshold pricing is deterministic for the MVP.",
                links="billing.pricing.apply_discount",
                signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
                body="    return 0",
            ),
        ),
    )
    assert parsed.blocks[1].anchor_id == "billing.pricing.choose_discount_strategy"


def test_current_parser_contract_treats_noncanonical_but_parsable_block_order_as_hard_error(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.belief Threshold pricing is deterministic for the MVP.\n"
            "# @grace.complexity 6\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    error, _ = parse_failure(tmp_path, content)
    assert "invalid_block_annotation_order" in error_codes(error)


def test_two_anchor_annotations_before_one_block_are_hard_error(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.first\n"
            "# @grace.complexity 1\n"
            "# @grace.anchor billing.pricing.second\n"
            "# @grace.complexity 1\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    error, _ = parse_failure(tmp_path, content)
    assert "orphan_block_annotations" in error_codes(error)


@pytest.mark.parametrize("annotation_line", ["# @grace.complexity 1", "# @grace.belief Some belief", "# @grace.links billing.pricing.x"])
def test_block_annotation_without_anchor_is_hard_error(tmp_path: Path, annotation_line: str) -> None:
    content = make_file(
        (
            f"{annotation_line}\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    error, _ = parse_failure(tmp_path, content)
    assert "block_annotation_without_anchor" in error_codes(error)


def test_ambiguous_or_unresolvable_binding_is_hard_error(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 1\n"
            "pass\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return price - ((price * percent) // 100)"
        )
    )

    error, _ = parse_failure(tmp_path, content)
    assert "arbitrary_code_between_annotations_and_block" in error_codes(error)


def test_anchor_starting_with_module_id_parses_successfully(tmp_path: Path) -> None:
    parsed = parse_success(tmp_path, make_file(function_block(anchor="billing.pricing.apply_discount", complexity="1")))
    assert parsed.blocks[0].anchor_id.startswith(parsed.module.module_id)


def test_current_parser_contract_is_neutral_to_anchor_namespace_prefix(tmp_path: Path) -> None:
    # This is intentionally not treated as a parser hard error. Namespace policy belongs to a future validator/linter layer.
    parsed = parse_success(tmp_path, make_file(function_block(anchor="external.apply_discount", complexity="1")))
    assert parsed.blocks[0].anchor_id == "external.apply_discount"


def test_successful_parse_returns_expected_typed_model_shape(tmp_path: Path) -> None:
    content = make_file(
        function_block(anchor="billing.pricing.apply_discount", complexity="1"),
        function_block(
            anchor="billing.pricing.choose_discount_strategy",
            complexity="6",
            belief="Threshold pricing is deterministic for the MVP.",
            links="billing.pricing.apply_discount",
            signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
            body="    return 0",
        ),
        header=module_header(
            purpose="Determine discount strategy and apply discounts.",
            interfaces="apply_discount(price:int, percent:int) -> int; choose_discount_strategy(customer_tier:str, cart_total:int) -> int",
            invariants=(
                "Discount percent must never be negative.",
                "Anchor ids are stable unless semantics change.",
            ),
        ),
    )

    parsed = parse_success(tmp_path, content)
    assert isinstance(parsed, MODELS.GraceFileModel)
    assert parsed.module.module_id == "billing.pricing"
    assert len(parsed.blocks) == 2
    assert parsed.module.invariants == (
        "Discount percent must never be negative.",
        "Anchor ids are stable unless semantics change.",
    )

    strategy_block = parsed.blocks[1]
    assert strategy_block.anchor_id == "billing.pricing.choose_discount_strategy"
    assert strategy_block.complexity == 6
    assert strategy_block.belief == "Threshold pricing is deterministic for the MVP."
    assert strategy_block.links == ("billing.pricing.apply_discount",)
    assert strategy_block.kind is MODELS.BlockKind.FUNCTION
    assert strategy_block.symbol_name == "choose_discount_strategy"


def test_failure_exception_api_raises_on_hard_error(tmp_path: Path) -> None:
    content = make_file(function_block(complexity="6"))
    with pytest.raises(PARSER.GraceParseError):
        PARSER.parse_python_file(write_temp_python_file(tmp_path, content))


def test_try_parse_returns_failure_result_instead_of_raising(tmp_path: Path) -> None:
    content = make_file(function_block(complexity="6"))
    path = write_temp_python_file(tmp_path, content)
    result = PARSER.try_parse_python_file(path)
    assert isinstance(result, MODELS.GraceParseFailure)
    assert result.ok is False


def test_failure_result_contains_diagnostic_information(tmp_path: Path) -> None:
    result = assert_failure_result(tmp_path, make_file(function_block(complexity="6")))
    assert any(issue.message for issue in result.errors)
    assert any(issue.code is MODELS.ParseErrorCode.MISSING_REQUIRED_BELIEF for issue in result.errors)


def test_success_result_contains_grace_file_model(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()))
    result = PARSER.try_parse_python_file(path)
    assert isinstance(result, MODELS.GraceParseSuccess)
    assert result.ok is True
    assert isinstance(result.file, MODELS.GraceFileModel)


def test_parser_is_deterministic_for_same_valid_file(tmp_path: Path) -> None:
    content = make_file(
        function_block(anchor="billing.pricing.apply_discount", complexity="1"),
        function_block(
            anchor="billing.pricing.choose_discount_strategy",
            complexity="6",
            belief="Threshold pricing is deterministic for the MVP.",
            links="billing.pricing.apply_discount",
            signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
            body="    return 0",
        ),
    )

    path = write_temp_python_file(tmp_path, content)
    first = PARSER.parse_python_file(path)
    second = PARSER.parse_python_file(path)

    assert first.model_dump(mode="python") == second.model_dump(mode="python")


def test_parser_normalizes_links_stably_between_runs(tmp_path: Path) -> None:
    content = make_file(
        function_block(anchor="billing.pricing.apply_discount", complexity="1"),
        function_block(
            anchor="billing.pricing.compute_base_discount",
            complexity="1",
            signature="def compute_base_discount() -> int:",
            body="    return 0",
        ),
        function_block(
            anchor="billing.pricing.choose_discount_strategy",
            complexity="6",
            belief="Threshold pricing is deterministic for the MVP.",
            links="billing.pricing.apply_discount, billing.pricing.compute_base_discount",
            signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
            body="    return 0",
        ),
    )

    path = write_temp_python_file(tmp_path, content)
    first = PARSER.parse_python_file(path)
    second = PARSER.parse_python_file(path)

    assert first.blocks[2].links == second.blocks[2].links == (
        "billing.pricing.apply_discount",
        "billing.pricing.compute_base_discount",
    )


def test_golden_minimal_valid_function_only_file(tmp_path: Path) -> None:
    parsed = parse_success(tmp_path, make_file(function_block()))
    assert parsed.module.module_id == "billing.pricing"
    assert len(parsed.blocks) == 1


def test_golden_valid_file_with_class_method_and_decorator(tmp_path: Path) -> None:
    content = make_file(
        (
            "# @grace.anchor billing.pricing.DiscountPolicy\n"
            "# @grace.complexity 1\n"
            "@dataclass\n"
            "class DiscountPolicy:\n"
            "    # @grace.anchor billing.pricing.DiscountPolicy.choose_discount_strategy\n"
            "    # @grace.complexity 6\n"
            "    # @grace.belief Threshold pricing is deterministic for the MVP.\n"
            "    @staticmethod\n"
            "    def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:\n"
            "        return 0"
        )
    )

    parsed = parse_success(tmp_path, content)
    assert [block.kind for block in parsed.blocks] == [MODELS.BlockKind.CLASS, MODELS.BlockKind.METHOD]


def test_golden_invalid_file_with_multiple_grammar_violations_reports_multiple_errors(tmp_path: Path) -> None:
    content = (
        "# @grace.module billing.pricing\n"
        "# @grace.purpose Determine pricing behavior.\n"
        "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n\n"
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 11\n"
        "x = 1\n\n"
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 6\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return price\n"
    )

    error, _ = parse_failure(tmp_path, content)
    codes = error_codes(error)

    assert len(error.errors) >= 3
    assert "missing_required_module_annotation" in codes
    assert "invalid_complexity" in codes
    assert "arbitrary_code_between_annotations_and_block" in codes
    assert "missing_required_belief" in codes
