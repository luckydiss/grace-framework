from __future__ import annotations

import importlib.util
import sys
import textwrap
import types
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_foundation_modules():
    for module_name in ("grace", "grace.models", "grace.parser", "grace.validator", "grace.linter", "grace.patcher"):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "validator", "linter", "patcher"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["models"], loaded["parser"], loaded["validator"], loaded["linter"], loaded["patcher"]


MODELS, PARSER, VALIDATOR, LINTER, PATCHER = load_foundation_modules()


def write_temp_python_file(tmp_path: Path, content: str, name: str = "sample.py") -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_patcher_files"
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


def test_patch_block_successfully_replaces_function_block(tmp_path: Path) -> None:
    path = write_temp_python_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount"),
            function_block(
                anchor="billing.pricing.keep_original",
                signature="def keep_original() -> int:",
                body="    return 1",
            ),
        ),
        name="pricing.py",
    )
    replacement = (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    discounted = price - ((price * percent) // 100)\n"
        "    return max(discounted, 0)\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement)

    assert isinstance(result, PATCHER.PatchSuccess)
    assert result.ok is True
    assert result.identity_preserved is True
    assert result.parse.status is PATCHER.PatchStepStatus.PASSED
    assert result.validation.status is PATCHER.PatchStepStatus.PASSED
    assert result.rollback_performed is False
    assert result.before_hash != result.after_hash
    assert result.file.blocks[0].anchor_id == "billing.pricing.apply_discount"
    assert "max(discounted, 0)" in path.read_text(encoding="utf-8")


def test_patch_block_successfully_replaces_method_block(tmp_path: Path) -> None:
    path = write_temp_python_file(
        tmp_path,
        make_file(
            (
                "class DiscountPolicy:\n"
                "    # @grace.anchor billing.pricing.DiscountPolicy.choose_discount_strategy\n"
                "    # @grace.complexity 1\n"
                "    def choose_discount_strategy(self, customer_tier: str) -> int:\n"
                "        return 0\n"
            )
        ),
        name="policy.py",
    )
    replacement = (
        "    # @grace.anchor billing.pricing.DiscountPolicy.choose_discount_strategy\n"
        "    # @grace.complexity 2\n"
        "    def choose_discount_strategy(self, customer_tier: str) -> int:\n"
        "        if customer_tier == \"vip\":\n"
        "            return 10\n"
        "        return 0\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.DiscountPolicy.choose_discount_strategy", replacement)

    assert isinstance(result, PATCHER.PatchSuccess)
    assert result.file.blocks[0].kind is MODELS.BlockKind.METHOD
    assert "return 10" in path.read_text(encoding="utf-8")


def test_patch_block_successfully_replaces_class_block(tmp_path: Path) -> None:
    path = write_temp_python_file(
        tmp_path,
        make_file(
            (
                "# @grace.anchor billing.pricing.DiscountPolicy\n"
                "# @grace.complexity 1\n"
                "class DiscountPolicy:\n"
                "    # @grace.anchor billing.pricing.DiscountPolicy.choose_discount_strategy\n"
                "    # @grace.complexity 1\n"
                "    def choose_discount_strategy(self) -> int:\n"
                "        return 0\n"
            )
        ),
        name="policy.py",
    )
    replacement = (
        "# @grace.anchor billing.pricing.DiscountPolicy\n"
        "# @grace.complexity 2\n"
        "class DiscountPolicy:\n"
        "    # @grace.anchor billing.pricing.DiscountPolicy.choose_discount_strategy\n"
        "    # @grace.complexity 2\n"
        "    def choose_discount_strategy(self) -> int:\n"
        "        return 5\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.DiscountPolicy", replacement)

    assert isinstance(result, PATCHER.PatchSuccess)
    assert any(block.anchor_id == "billing.pricing.DiscountPolicy" for block in result.file.blocks)
    assert "return 5" in path.read_text(encoding="utf-8")


def test_patch_block_returns_failure_for_unknown_anchor_id(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = path.read_text(encoding="utf-8")

    result = PATCHER.patch_block(path, "billing.pricing.unknown", function_block())

    assert isinstance(result, PATCHER.PatchFailure)
    assert result.stage is PATCHER.PatchFailureStage.TARGET_LOOKUP
    assert path.read_text(encoding="utf-8") == original_text


def test_patch_block_does_not_modify_unrelated_blocks(tmp_path: Path) -> None:
    path = write_temp_python_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.pricing.apply_discount"),
            function_block(
                anchor="billing.pricing.keep_original",
                signature="def keep_original() -> int:",
                body="    return 7",
            ),
        ),
        name="pricing.py",
    )
    original_text = path.read_text(encoding="utf-8")
    replacement = (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return 99\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement)

    assert isinstance(result, PATCHER.PatchSuccess)
    updated_text = path.read_text(encoding="utf-8")
    assert "def keep_original() -> int:\n    return 7" in updated_text
    assert original_text.count("keep_original") == updated_text.count("keep_original")


def test_patch_block_rolls_back_on_parser_failure(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = path.read_text(encoding="utf-8")
    invalid_replacement = (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 6\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return price\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", invalid_replacement)

    assert isinstance(result, PATCHER.PatchFailure)
    assert result.stage is PATCHER.PatchFailureStage.PARSE
    assert result.rollback_performed is False
    assert result.parse_errors
    assert path.read_text(encoding="utf-8") == original_text


def test_patch_block_rejects_replacement_with_different_anchor_id_and_rolls_back(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = path.read_text(encoding="utf-8")
    replacement = (
        "# @grace.anchor billing.pricing.other_block\n"
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return price\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement)

    assert isinstance(result, PATCHER.PatchFailure)
    assert result.stage is PATCHER.PatchFailureStage.IDENTITY
    assert path.read_text(encoding="utf-8") == original_text


def test_patch_block_rejects_replacement_without_anchor_and_rolls_back(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = path.read_text(encoding="utf-8")
    replacement = (
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return price\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement)

    assert isinstance(result, PATCHER.PatchFailure)
    assert result.stage is PATCHER.PatchFailureStage.IDENTITY
    assert path.read_text(encoding="utf-8") == original_text


def test_patch_block_rolls_back_on_validator_failure(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = path.read_text(encoding="utf-8")
    invalid_replacement = (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 1\n"
        "def other_name(price: int, percent: int) -> int:\n"
        "    return price\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", invalid_replacement)

    assert isinstance(result, PATCHER.PatchFailure)
    assert result.stage is PATCHER.PatchFailureStage.VALIDATE
    assert result.rollback_performed is False
    assert result.validation_issues
    assert path.read_text(encoding="utf-8") == original_text


def test_patch_block_succeeds_even_when_linter_returns_warnings(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement = (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 6\n"
        "# @grace.belief maybe\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return price\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement)

    assert isinstance(result, PATCHER.PatchSuccess)
    assert any(issue.code is LINTER.LintIssueCode.WEAK_BELIEF for issue in result.lint_issues)
    assert "# @grace.belief maybe" in path.read_text(encoding="utf-8")


def test_patch_block_is_deterministic_on_repeated_application(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement = (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return 42\n"
    )

    first = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement)
    first_text = path.read_text(encoding="utf-8")
    second = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement)
    second_text = path.read_text(encoding="utf-8")

    assert isinstance(first, PATCHER.PatchSuccess)
    assert isinstance(second, PATCHER.PatchSuccess)
    assert first.file.model_dump(mode="python") == second.file.model_dump(mode="python")
    assert first_text == second_text


def test_patch_block_dry_run_does_not_modify_file_and_returns_success(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    original_text = path.read_text(encoding="utf-8")
    replacement = (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return 42\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement, dry_run=True)

    assert isinstance(result, PATCHER.PatchSuccess)
    assert result.dry_run is True
    assert result.identity_preserved is True
    assert result.parse.status is PATCHER.PatchStepStatus.PASSED
    assert result.validation.status is PATCHER.PatchStepStatus.PASSED
    assert result.rollback_performed is False
    assert "return 42" not in path.read_text(encoding="utf-8")
    assert path.read_text(encoding="utf-8") == original_text


def test_patch_block_returns_preview_diff_for_dry_run(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement = (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return 42\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement, dry_run=True)

    assert isinstance(result, PATCHER.PatchSuccess)
    assert "---" in result.preview
    assert "+++ " in result.preview
    assert "return 42" in result.preview
    assert "return price - ((price * percent) // 100)" in result.preview


def test_successful_patch_preserves_anchor_identity_exactly(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement = (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return price\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement)

    assert isinstance(result, PATCHER.PatchSuccess)
    assert result.anchor_id == "billing.pricing.apply_discount"
    assert result.file.blocks[0].anchor_id == "billing.pricing.apply_discount"
    assert "# @grace.anchor billing.pricing.apply_discount" in path.read_text(encoding="utf-8")


def test_patched_file_can_be_reparsed_into_valid_grace_file_model(tmp_path: Path) -> None:
    path = write_temp_python_file(tmp_path, make_file(function_block()), name="pricing.py")
    replacement = (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return price\n"
    )

    result = PATCHER.patch_block(path, "billing.pricing.apply_discount", replacement)
    reparsed = PARSER.parse_python_file(path)
    validation = VALIDATOR.validate_file(reparsed)

    assert isinstance(result, PATCHER.PatchSuccess)
    assert isinstance(reparsed, MODELS.GraceFileModel)
    assert isinstance(validation, VALIDATOR.ValidationSuccess)
    assert reparsed.model_dump(mode="python") == result.file.model_dump(mode="python")
