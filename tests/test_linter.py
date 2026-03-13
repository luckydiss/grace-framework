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
    for module_name in ("grace", "grace.models", "grace.parser", "grace.language_adapter", "grace.python_adapter", "grace.validator", "grace.linter"):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "validator", "linter"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["models"], loaded["parser"], loaded["validator"], loaded["linter"]


MODELS, PARSER, VALIDATOR, LINTER = load_foundation_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER, VALIDATOR, LINTER
    load_foundation_modules.cache_clear()
    MODELS, PARSER, VALIDATOR, LINTER = load_foundation_modules()


def write_temp_python_file(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_linter_files"
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
    invariants: tuple[str, ...] = ("Discount percent must never be negative.", "Anchor ids remain stable for unchanged semantics."),
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


def lint_codes(result) -> set[str]:
    assert isinstance(result, LINTER.LintFailure)
    return {issue.code.value for issue in result.issues}


def test_lint_file_accepts_valid_file_with_no_issues(tmp_path: Path) -> None:
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

    result = LINTER.lint_file(grace_file)

    assert isinstance(result, LINTER.LintSuccess)
    assert result.ok is True


def test_lint_file_warns_on_weak_purpose_placeholder(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block(), header=module_header(purpose="todo")))

    result = LINTER.lint_file(grace_file)

    assert isinstance(result, LINTER.LintFailure)
    assert "weak_module_text" in lint_codes(result)


def test_lint_file_warns_on_weak_invariant_placeholder(tmp_path: Path) -> None:
    grace_file = parse_file(
        tmp_path,
        make_file(function_block(), header=module_header(invariants=("tbd", "Anchor ids remain stable for unchanged semantics."))),
    )

    result = LINTER.lint_file(grace_file)

    assert isinstance(result, LINTER.LintFailure)
    assert "weak_module_text" in lint_codes(result)


def test_lint_file_warns_on_weak_belief_for_complex_block(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block(complexity="6", belief="maybe")))

    result = LINTER.lint_file(grace_file)

    assert isinstance(result, LINTER.LintFailure)
    assert "weak_belief" in lint_codes(result)


def test_lint_file_warns_on_excessively_long_belief_and_purpose(tmp_path: Path) -> None:
    long_text = "Signal " * 60
    grace_file = parse_file(
        tmp_path,
        make_file(
            function_block(complexity="6", belief=long_text),
            header=module_header(purpose=long_text),
        ),
    )

    result = LINTER.lint_file(grace_file)

    assert isinstance(result, LINTER.LintFailure)
    assert "long_text" in lint_codes(result)


def test_lint_file_warns_on_duplicate_links_when_model_allows_it(tmp_path: Path) -> None:
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
    duplicated = grace_file.blocks[1].model_copy(update={"links": ("billing.pricing.apply_discount", "billing.pricing.apply_discount")})
    grace_file = grace_file.model_copy(update={"blocks": (grace_file.blocks[0], duplicated)})

    result = LINTER.lint_file(grace_file)

    assert isinstance(result, LINTER.LintFailure)
    assert "duplicate_link" in lint_codes(result)


def test_lint_file_accumulates_multiple_warnings(tmp_path: Path) -> None:
    long_text = "Signal " * 60
    grace_file = parse_file(
        tmp_path,
        make_file(
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="tbd",
                signature="def choose_discount_strategy(customer_tier: str, cart_total: int) -> int:",
                body="    return 0",
            ),
            header=module_header(purpose="todo", invariants=("...",)),
        ),
    )
    duplicated = grace_file.blocks[0].model_copy(
        update={
            "links": ("billing.pricing.choose_discount_strategy", "billing.pricing.choose_discount_strategy"),
            "belief": long_text,
        }
    )
    grace_file = grace_file.model_copy(update={"blocks": (duplicated,)})

    result = LINTER.lint_file(grace_file)

    assert isinstance(result, LINTER.LintFailure)
    assert len(result.issues) >= 4
    codes = lint_codes(result)
    assert "weak_module_text" in codes
    assert "long_text" in codes
    assert "duplicate_link" in codes
    assert "too_few_invariants" in codes


def test_lint_project_aggregates_warnings_across_files(tmp_path: Path) -> None:
    file_a = parse_file(tmp_path, make_file(function_block(), header=module_header(purpose="todo")), name="a.py")
    file_b = parse_file(tmp_path, make_file(function_block(complexity="6", belief="maybe"), header=module_header(module_id="billing.tax")), name="b.py")

    result = LINTER.lint_project([file_a, file_b])

    assert isinstance(result, LINTER.LintFailure)
    assert len(result.issues) >= 2
    codes = lint_codes(result)
    assert "weak_module_text" in codes
    assert "weak_belief" in codes


def test_linter_does_not_rerun_parser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block()))

    def _boom(*args, **kwargs):
        raise AssertionError("linter must not call parser")

    monkeypatch.setattr(PARSER, "parse_python_file", _boom)

    result = LINTER.lint_file(grace_file)

    assert isinstance(result, LINTER.LintSuccess)
    assert result.ok is True


def test_linter_does_not_duplicate_validator_namespace_rule(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block()))
    broken = grace_file.blocks[0].model_copy(update={"anchor_id": "external.apply_discount"})
    grace_file = grace_file.model_copy(update={"blocks": (broken,)})

    lint_result = LINTER.lint_file(grace_file)
    validator_result = VALIDATOR.validate_file(grace_file)

    assert isinstance(validator_result, VALIDATOR.ValidationFailure)
    assert "anchor_module_prefix_mismatch" in {issue.code.value for issue in validator_result.issues}
    # Namespace-prefix enforcement is intentionally left to validator, not linter.
    assert isinstance(lint_result, LINTER.LintSuccess)


def test_lint_file_warns_on_large_block_line_span(tmp_path: Path) -> None:
    large_body = "\n".join(f"    value_{index} = {index}" for index in range(45))
    grace_file = parse_file(
        tmp_path,
        make_file(
            function_block(
                complexity="1",
                body=f"{large_body}\n    return value_44",
            )
        ),
    )

    result = LINTER.lint_file(grace_file)

    assert isinstance(result, LINTER.LintFailure)
    assert "large_block" in lint_codes(result)
