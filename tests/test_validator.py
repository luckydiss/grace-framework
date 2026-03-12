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
    for module_name in ("grace", "grace.models", "grace.parser", "grace.validator"):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "validator"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["models"], loaded["parser"], loaded["validator"]


MODELS, PARSER, VALIDATOR = load_foundation_modules()


def write_temp_python_file(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_validator_files"
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


def issue_codes(result) -> set[str]:
    assert isinstance(result, VALIDATOR.ValidationFailure)
    return {issue.code.value for issue in result.issues}


def test_validate_file_accepts_valid_single_file(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block()))

    result = VALIDATOR.validate_file(grace_file)

    assert isinstance(result, VALIDATOR.ValidationSuccess)
    assert result.ok is True
    assert result.scope == "file"


def test_validate_project_accepts_valid_project_with_two_files(tmp_path: Path) -> None:
    file_a = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount"),
            header=module_header(module_id="billing.pricing"),
        ),
        name="pricing.py",
    )
    file_b = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.tax.apply_tax", signature="def apply_tax(amount: int) -> int:", body="    return amount"),
            header=module_header(module_id="billing.tax"),
        ),
        name="tax.py",
    )

    result = VALIDATOR.validate_project([file_a, file_b])

    assert isinstance(result, VALIDATOR.ValidationSuccess)
    assert result.ok is True
    assert result.scope == "project"


def test_validate_file_rejects_invalid_module_id_format(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block(), header=module_header(module_id="billing_pricing")))

    result = VALIDATOR.validate_file(grace_file)

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert "invalid_module_id" in issue_codes(result)


def test_validate_file_rejects_invalid_anchor_id_format(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block(anchor="apply_discount")))

    result = VALIDATOR.validate_file(grace_file)

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert "invalid_anchor_id" in issue_codes(result)


def test_validate_file_rejects_anchor_not_prefixed_by_module_id(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block(anchor="external.apply_discount")))

    result = VALIDATOR.validate_file(grace_file)

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert "anchor_module_prefix_mismatch" in issue_codes(result)


def test_validate_file_rejects_empty_purpose_interfaces_and_invariants(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block()))
    broken_module = grace_file.module.model_copy(update={"purpose": "   ", "interfaces": "\t", "invariants": ("ok", "   ")})
    broken_file = grace_file.model_copy(update={"module": broken_module})

    result = VALIDATOR.validate_file(broken_file)

    assert isinstance(result, VALIDATOR.ValidationFailure)
    codes = issue_codes(result)
    assert "empty_module_field" in codes
    assert "empty_invariant" in codes


def test_validate_file_rejects_empty_belief_when_complexity_is_high(tmp_path: Path) -> None:
    grace_file = parse_file(
        tmp_path,
        make_file(function_block(complexity="6", belief="Threshold pricing is deterministic for the MVP.")),
    )
    broken_block = grace_file.blocks[0].model_copy(update={"belief": "   "})
    broken_file = grace_file.model_copy(update={"blocks": (broken_block,)})

    result = VALIDATOR.validate_file(broken_file)

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert "missing_belief" in issue_codes(result)


def test_validate_file_rejects_broken_file_level_link(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block()))
    broken_block = grace_file.blocks[0].model_copy(update={"links": ("billing.pricing.missing_anchor",)})
    broken_file = grace_file.model_copy(update={"blocks": (broken_block,)})

    result = VALIDATOR.validate_file(broken_file)

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert "broken_link" in issue_codes(result)


def test_validate_project_rejects_broken_project_level_link(tmp_path: Path) -> None:
    file_a = parse_file(tmp_path, make_file(function_block(anchor="billing.pricing.apply_discount")), name="pricing.py")
    file_b = parse_file(tmp_path, make_file(function_block(anchor="billing.tax.apply_tax"), header=module_header(module_id="billing.tax")), name="tax.py")
    broken_block = file_a.blocks[0].model_copy(update={"links": ("billing.tax.missing_anchor",)})
    file_a = file_a.model_copy(update={"blocks": (broken_block,)})

    result = VALIDATOR.validate_project([file_a, file_b])

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert "broken_link" in issue_codes(result)


def test_validate_project_allows_cross_file_link_when_target_exists(tmp_path: Path) -> None:
    file_a = parse_file(tmp_path, make_file(function_block(anchor="billing.pricing.apply_discount")), name="pricing.py")
    file_b = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.tax.apply_tax", signature="def apply_tax(amount: int) -> int:", body="    return amount"),
            header=module_header(module_id="billing.tax"),
        ),
        name="tax.py",
    )
    linked_block = file_a.blocks[0].model_copy(update={"links": ("billing.tax.apply_tax",)})
    file_a = file_a.model_copy(update={"blocks": (linked_block,)})

    result = VALIDATOR.validate_project([file_a, file_b])

    assert isinstance(result, VALIDATOR.ValidationSuccess)
    assert result.ok is True


def test_validate_project_rejects_duplicate_module_id_across_files(tmp_path: Path) -> None:
    file_a = parse_file(tmp_path, make_file(function_block(anchor="billing.pricing.apply_discount")), name="pricing_a.py")
    file_b = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.compute_discount", signature="def compute_discount() -> int:", body="    return 0"),
            header=module_header(module_id="billing.pricing"),
        ),
        name="pricing_b.py",
    )

    result = VALIDATOR.validate_project([file_a, file_b])

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert "duplicate_module_id" in issue_codes(result)


def test_validate_project_rejects_duplicate_anchor_id_across_files(tmp_path: Path) -> None:
    file_a = parse_file(tmp_path, make_file(function_block(anchor="billing.pricing.apply_discount")), name="pricing_a.py")
    file_b = parse_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount", signature="def apply_discount_v2() -> int:", body="    return 0"),
            header=module_header(module_id="billing.tax"),
        ),
        name="pricing_b.py",
    )

    result = VALIDATOR.validate_project([file_a, file_b])

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert "duplicate_anchor_id" in issue_codes(result)


def test_validate_file_accumulates_multiple_issues(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block()))
    broken_block = grace_file.blocks[0].model_copy(
        update={
            "anchor_id": "badanchor",
            "kind": "weird_kind",
            "belief": "   ",
            "complexity": 7,
            "links": ("billing.pricing.missing_anchor",),
        }
    )
    broken_module = grace_file.module.model_copy(update={"module_id": "badmodule", "purpose": "   ", "interfaces": "   ", "invariants": (" ",)})
    broken_file = grace_file.model_copy(update={"module": broken_module, "blocks": (broken_block,)})

    result = VALIDATOR.validate_file(broken_file)

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert len(result.issues) >= 6
    codes = issue_codes(result)
    assert "invalid_module_id" in codes
    assert "invalid_anchor_id" in codes
    assert "invalid_block_kind" in codes
    assert "missing_belief" in codes
    assert "broken_link" in codes
    assert "empty_module_field" in codes


def test_validate_file_does_not_reparse_source_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block()))

    def _boom(*args, **kwargs):
        raise AssertionError("validator must not call parser")

    monkeypatch.setattr(PARSER, "parse_python_file", _boom)

    result = VALIDATOR.validate_file(grace_file)

    assert isinstance(result, VALIDATOR.ValidationSuccess)
    assert result.ok is True


def test_validate_file_rejects_symbol_name_anchor_tail_mismatch(tmp_path: Path) -> None:
    grace_file = parse_file(tmp_path, make_file(function_block()))
    broken_block = grace_file.blocks[0].model_copy(update={"anchor_id": "billing.pricing.other_name"})
    broken_file = grace_file.model_copy(update={"blocks": (broken_block,)})

    result = VALIDATOR.validate_file(broken_file)

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert "symbol_anchor_mismatch" in issue_codes(result)


def test_validate_file_rejects_invalid_method_namespace_when_reliably_checkable(tmp_path: Path) -> None:
    grace_file = parse_file(
        tmp_path,
        make_file(
            "class DiscountPolicy:\n"
            "    # @grace.anchor billing.pricing.DiscountPolicy.choose_discount_strategy\n"
            "    # @grace.complexity 1\n"
            "    def choose_discount_strategy(self) -> int:\n"
            "        return 0"
        ),
    )
    broken_block = grace_file.blocks[0].model_copy(update={"anchor_id": "billing.pricing.choose_discount_strategy"})
    broken_file = grace_file.model_copy(update={"blocks": (broken_block,)})

    result = VALIDATOR.validate_file(broken_file)

    assert isinstance(result, VALIDATOR.ValidationFailure)
    assert "invalid_method_namespace" in issue_codes(result)
