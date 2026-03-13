from __future__ import annotations

from pathlib import Path

from tests._adapter_harness import ROOT, minimal_common_shape, normalized_semantic_shape


def test_python_and_typescript_parity_fixtures_have_matching_semantic_structure() -> None:
    python_shape = normalized_semantic_shape(ROOT / "examples" / "parity" / "python" / "basic.py")
    typescript_shape = normalized_semantic_shape(ROOT / "examples" / "parity" / "typescript" / "basic.ts")

    assert python_shape["module_id"] == typescript_shape["module_id"] == "demo.parity"
    assert python_shape["block_count"] == typescript_shape["block_count"] == 4
    assert python_shape["blocks"] == typescript_shape["blocks"]


def test_python_typescript_and_go_parity_fixtures_match_minimal_common_shape() -> None:
    python_shape = minimal_common_shape(ROOT / "examples" / "parity" / "python" / "basic.py")
    typescript_shape = minimal_common_shape(ROOT / "examples" / "parity" / "typescript" / "basic.ts")
    go_shape = minimal_common_shape(ROOT / "examples" / "parity" / "go" / "basic.go")

    assert python_shape["module_id"] == typescript_shape["module_id"] == go_shape["module_id"] == "demo.parity"
    assert python_shape["block_count"] == typescript_shape["block_count"] == go_shape["block_count"] == 4
    assert python_shape["blocks"] == typescript_shape["blocks"] == go_shape["blocks"]


def test_parity_fixtures_preserve_expected_anchor_order() -> None:
    python_shape = normalized_semantic_shape(ROOT / "examples" / "parity" / "python" / "basic.py")

    assert [block["anchor_id"] for block in python_shape["blocks"]] == [
        "demo.parity.example",
        "demo.parity.load_example",
        "demo.parity.ExampleService",
        "demo.parity.ExampleService.run",
    ]
