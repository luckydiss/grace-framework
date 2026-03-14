from __future__ import annotations

from pathlib import Path

from grace.bootstrapper import BootstrapFailure, BootstrapFailureStage, bootstrap_path
from grace.parser import parse_python_file


def writable_dir(tmp_path: Path, name: str) -> Path:
    target = tmp_path.parent / f"{tmp_path.name}_{name}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_bootstrap_preview_generates_python_header_and_anchor(tmp_path: Path) -> None:
    source_root = writable_dir(tmp_path, "bootstrap_preview") / "src"
    source_path = write_text(
        source_root / "billing" / "tax.py",
        "def apply_tax(price: int) -> int:\n    return price + 1\n",
    )

    result = bootstrap_path(source_root)
    assert result.ok is True
    assert len(result.file_changes) == 1

    file_change = result.file_changes[0]
    assert file_change.header_added is True
    assert file_change.module_id == "billing.tax"
    assert [anchor.anchor_id for anchor in file_change.generated_anchors] == [
        "billing.tax.apply_tax"
    ]
    assert source_path.read_text(encoding="utf-8").startswith("def apply_tax")


def test_bootstrap_apply_writes_file_and_makes_it_parseable(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "bootstrap_apply")
    source_path = write_text(
        workspace / "service.py",
        "def run() -> int:\n    return 1\n",
    )

    result = bootstrap_path(source_path, apply=True)
    assert result.ok is True

    parsed = parse_python_file(source_path)
    expected_module_id = f"{workspace.name}.service"
    assert parsed.module.module_id == expected_module_id
    assert [block.anchor_id for block in parsed.blocks] == [f"{expected_module_id}.run"]


def test_bootstrap_adds_only_missing_block_annotations(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "bootstrap_partial")
    source_path = write_text(
        workspace / "module.py",
        (
            "# @grace.module module\n"
            "# @grace.purpose TODO\n"
            "# @grace.interfaces TODO\n"
            "# @grace.invariant TODO\n\n"
            "# @grace.anchor module.first\n"
            "# @grace.complexity 1\n"
            "def first() -> int:\n"
            "    return 1\n\n"
            "def second() -> int:\n"
            "    return 2\n"
        ),
    )

    result = bootstrap_path(source_path)
    assert result.ok is True
    assert result.file_changes[0].header_added is False
    assert [anchor.anchor_id for anchor in result.file_changes[0].generated_anchors] == [
        "module.second"
    ]


def test_bootstrap_rolls_back_on_validation_failure(tmp_path: Path, monkeypatch) -> None:
    workspace = writable_dir(tmp_path, "bootstrap_rollback")
    source_path = write_text(
        workspace / "broken.py",
        "def run() -> int:\n    return 1\n",
    )
    original_text = source_path.read_text(encoding="utf-8")

    from grace import bootstrapper as bootstrapper_module

    def fail_validation(requested_path: Path):
        return ((), ("forced validation failure",), 0)

    monkeypatch.setattr(bootstrapper_module, "_validate_bootstrap_scope", fail_validation)
    result = bootstrap_path(source_path, apply=True)

    assert isinstance(result, BootstrapFailure)
    assert result.stage is BootstrapFailureStage.VALIDATE
    assert result.rollback_performed is True
    assert source_path.read_text(encoding="utf-8") == original_text
