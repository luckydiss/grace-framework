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
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.language_adapter",
        "grace.python_adapter",
        "grace.validator",
        "grace.linter",
        "grace.patcher",
        "grace.plan",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "validator", "linter", "patcher", "plan"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return (
        loaded["models"],
        loaded["parser"],
        loaded["validator"],
        loaded["linter"],
        loaded["patcher"],
        loaded["plan"],
    )


MODELS, PARSER, VALIDATOR, LINTER, PATCHER, PLAN = load_foundation_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER, VALIDATOR, LINTER, PATCHER, PLAN
    load_foundation_modules.cache_clear()
    MODELS, PARSER, VALIDATOR, LINTER, PATCHER, PLAN = load_foundation_modules()


def write_temp_file(tmp_path: Path, content: str, name: str) -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_plan_files"
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


def test_load_patch_plan_resolves_relative_paths(tmp_path: Path) -> None:
    target_path = write_temp_file(tmp_path, make_file(function_block()), "pricing.py")
    replacement_path = write_temp_file(
        tmp_path,
        (
            "# @grace.anchor billing.pricing.apply_discount\n"
            "# @grace.complexity 2\n"
            "def apply_discount(price: int, percent: int) -> int:\n"
            "    return 42\n"
        ),
        "replacement.py",
    )
    plan_dir = tmp_path.parent / f"{tmp_path.name}_plan_dir"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plan_dir / "plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "grace_version": "v1",
                "entries": [
                    {
                        "path": str(Path("..") / target_path.parent.name / target_path.name),
                        "anchor_id": "billing.pricing.apply_discount",
                        "operation": "replace_block",
                        "replacement_file": str(Path("..") / replacement_path.parent.name / replacement_path.name),
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    plan = PLAN.load_patch_plan(plan_path)
    payload = PLAN.plan_to_dict(plan)

    assert plan.grace_version == "v1"
    assert plan.entries[0].path == target_path.resolve()
    assert plan.entries[0].replacement_file == replacement_path.resolve()
    assert payload["entries"][0]["anchor_id"] == "billing.pricing.apply_discount"


def test_apply_patch_plan_successfully_applies_multiple_entries(tmp_path: Path) -> None:
    pricing_path = write_temp_file(
        tmp_path,
        make_file(function_block(anchor="billing.pricing.apply_discount")),
        "pricing.py",
    )
    tax_path = write_temp_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.tax.apply_tax", signature="def apply_tax(amount: int) -> int:", body="    return amount"),
            header=module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
        ),
        "tax.py",
    )
    plan = PLAN.PatchPlan(
        entries=(
            PLAN.PatchPlanEntry(
                path=pricing_path,
                anchor_id="billing.pricing.apply_discount",
                replacement_source=(
                    "# @grace.anchor billing.pricing.apply_discount\n"
                    "# @grace.complexity 2\n"
                    "def apply_discount(price: int, percent: int) -> int:\n"
                    "    return 42\n"
                ),
            ),
            PLAN.PatchPlanEntry(
                path=tax_path,
                anchor_id="billing.tax.apply_tax",
                replacement_source=(
                    "# @grace.anchor billing.tax.apply_tax\n"
                    "# @grace.complexity 2\n"
                    "def apply_tax(amount: int) -> int:\n"
                    "    return amount + 1\n"
                ),
            ),
        )
    )

    result = PLAN.apply_patch_plan(plan)

    assert isinstance(result, PLAN.ApplyPlanSuccess)
    assert result.applied_count == 2
    assert result.entry_count == 2
    assert all(entry.result.ok is True for entry in result.entries)
    assert "return 42" in pricing_path.read_text(encoding="utf-8")
    assert "return amount + 1" in tax_path.read_text(encoding="utf-8")


def test_apply_patch_plan_dry_run_does_not_modify_files(tmp_path: Path) -> None:
    pricing_path = write_temp_file(
        tmp_path,
        make_file(function_block(anchor="billing.pricing.apply_discount")),
        "pricing.py",
    )
    original_text = pricing_path.read_text(encoding="utf-8")
    plan = PLAN.PatchPlan(
        entries=(
            PLAN.PatchPlanEntry(
                path=pricing_path,
                anchor_id="billing.pricing.apply_discount",
                replacement_source=(
                    "# @grace.anchor billing.pricing.apply_discount\n"
                    "# @grace.complexity 2\n"
                    "def apply_discount(price: int, percent: int) -> int:\n"
                    "    return 42\n"
                ),
            ),
        )
    )

    result = PLAN.apply_patch_plan(plan, dry_run=True)

    assert isinstance(result, PLAN.ApplyPlanSuccess)
    assert result.dry_run is True
    assert result.preview is False
    assert result.entries[0].result.ok is True
    assert result.entries[0].result.dry_run is True
    assert pricing_path.read_text(encoding="utf-8") == original_text


def test_apply_patch_plan_preview_returns_diff_without_modifying_files(tmp_path: Path) -> None:
    pricing_path = write_temp_file(
        tmp_path,
        make_file(function_block(anchor="billing.pricing.apply_discount")),
        "pricing.py",
    )
    original_text = pricing_path.read_text(encoding="utf-8")
    plan = PLAN.PatchPlan(
        entries=(
            PLAN.PatchPlanEntry(
                path=pricing_path,
                anchor_id="billing.pricing.apply_discount",
                replacement_source=(
                    "# @grace.anchor billing.pricing.apply_discount\n"
                    "# @grace.complexity 2\n"
                    "def apply_discount(price: int, percent: int) -> int:\n"
                    "    return 42\n"
                ),
            ),
        )
    )

    result = PLAN.apply_patch_plan(plan, preview=True)

    assert isinstance(result, PLAN.ApplyPlanSuccess)
    assert result.dry_run is True
    assert result.preview is True
    assert "---" in result.entries[0].result.preview
    assert "return 42" in result.entries[0].result.preview
    assert pricing_path.read_text(encoding="utf-8") == original_text


def test_apply_patch_plan_rolls_back_all_disk_writes_when_later_entry_fails(tmp_path: Path) -> None:
    pricing_path = write_temp_file(
        tmp_path,
        make_file(function_block(anchor="billing.pricing.apply_discount")),
        "pricing.py",
    )
    tax_path = write_temp_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.tax.apply_tax", signature="def apply_tax(amount: int) -> int:", body="    return amount"),
            header=module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
        ),
        "tax.py",
    )
    later_path = write_temp_file(
        tmp_path,
        make_file(
            function_block(anchor="billing.audit.record", signature="def record() -> int:", body="    return 0"),
            header=module_header(module_id="billing.audit", interfaces="record() -> int"),
        ),
        "audit.py",
    )
    original_pricing_text = pricing_path.read_text(encoding="utf-8")
    original_tax_text = tax_path.read_text(encoding="utf-8")
    original_later_text = later_path.read_text(encoding="utf-8")
    plan = PLAN.PatchPlan(
        entries=(
            PLAN.PatchPlanEntry(
                path=pricing_path,
                anchor_id="billing.pricing.apply_discount",
                replacement_source=(
                    "# @grace.anchor billing.pricing.apply_discount\n"
                    "# @grace.complexity 2\n"
                    "def apply_discount(price: int, percent: int) -> int:\n"
                    "    return 42\n"
                ),
            ),
            PLAN.PatchPlanEntry(
                path=tax_path,
                anchor_id="billing.tax.missing_anchor",
                replacement_source=(
                    "# @grace.anchor billing.tax.missing_anchor\n"
                    "# @grace.complexity 2\n"
                    "def apply_tax(amount: int) -> int:\n"
                    "    return amount + 1\n"
                ),
            ),
            PLAN.PatchPlanEntry(
                path=later_path,
                anchor_id="billing.audit.record",
                replacement_source=(
                    "# @grace.anchor billing.audit.record\n"
                    "# @grace.complexity 2\n"
                    "def record() -> int:\n"
                    "    return 1\n"
                ),
            ),
        )
    )

    result = PLAN.apply_patch_plan(plan)

    assert isinstance(result, PLAN.ApplyPlanFailure)
    assert result.stage is PLAN.ApplyPlanFailureStage.ENTRY_FAILURE
    assert result.applied_count == 1
    assert result.failed_index == 1
    assert result.failed_path == tax_path
    assert result.failed_anchor_id == "billing.tax.missing_anchor"
    assert len(result.entries) == 2
    assert result.entries[0].result.ok is True
    assert result.entries[1].result.ok is False
    assert pricing_path.read_text(encoding="utf-8") == original_pricing_text
    assert tax_path.read_text(encoding="utf-8") == original_tax_text
    assert later_path.read_text(encoding="utf-8") == original_later_text


def test_apply_patch_plan_dry_run_normalizes_results_back_to_original_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_temp_file(tmp_path, make_file(function_block()), "pricing.py")
    stub_file = PARSER.parse_python_file(path)
    calls: list[tuple[Path, str, str, bool]] = []

    def fake_patch_block(target_path: Path, anchor_id: str, replacement_source: str, *, dry_run: bool = False):
        calls.append((target_path, anchor_id, replacement_source, dry_run))
        return PATCHER.PatchSuccess(
            path=target_path,
            anchor_id=anchor_id,
            dry_run=dry_run,
            parse=PATCHER.PatchStepResult(status=PATCHER.PatchStepStatus.PASSED),
            validation=PATCHER.PatchStepResult(status=PATCHER.PatchStepStatus.PASSED),
            rollback_performed=False,
            before_hash="before",
            after_hash="after",
            preview="preview",
            file=stub_file,
            lint_issues=(),
        )

    monkeypatch.setattr(PLAN, "patch_block", fake_patch_block)
    plan = PLAN.PatchPlan(
        entries=(
            PLAN.PatchPlanEntry(
                path=path,
                anchor_id="billing.pricing.apply_discount",
                replacement_source=(
                    "# @grace.anchor billing.pricing.apply_discount\n"
                    "# @grace.complexity 2\n"
                    "def apply_discount(price: int, percent: int) -> int:\n"
                    "    return 42\n"
                ),
            ),
        )
    )

    result = PLAN.apply_patch_plan(plan, dry_run=True)

    assert isinstance(result, PLAN.ApplyPlanSuccess)
    assert result.dry_run is True
    assert result.entries[0].path == path.resolve()
    assert result.entries[0].result.path == path.resolve()
    assert result.entries[0].result.dry_run is True
    assert result.entries[0].result.file.path == path.resolve()
    assert len(calls) == 1
    assert calls[0][0] != path.resolve()
    assert calls[0][1:] == (
        "billing.pricing.apply_discount",
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return 42\n",
        False,
    )


def test_apply_patch_plan_load_failure_taxonomy_stays_in_cli_layer(tmp_path: Path) -> None:
    invalid_plan_path = write_temp_file(tmp_path, "{not-json", "broken_plan.json")

    with pytest.raises(json.JSONDecodeError):
        PLAN.load_patch_plan(invalid_plan_path)
