from __future__ import annotations

from pathlib import Path

from grace.parser import parse_python_file


ROOT = Path(__file__).resolve().parents[1]


def _normalized_semantic_shape(path: Path) -> dict[str, object]:
    grace_file = parse_python_file(path)
    return {
        "module_id": grace_file.module.module_id,
        "block_count": len(grace_file.blocks),
        "blocks": [
            {
                "anchor_id": block.anchor_id,
                "kind": block.kind.value,
                "complexity": block.complexity,
                "links": list(block.links),
                "is_async": block.is_async,
            }
            for block in grace_file.blocks
        ],
    }


def _minimal_common_shape(path: Path) -> dict[str, object]:
    grace_file = parse_python_file(path)
    return {
        "module_id": grace_file.module.module_id,
        "block_count": len(grace_file.blocks),
        "blocks": [
            {
                "anchor_id": block.anchor_id,
                "complexity": block.complexity,
                "links": list(block.links),
            }
            for block in grace_file.blocks
        ],
    }


def test_python_and_typescript_parity_fixtures_have_matching_semantic_structure() -> None:
    python_shape = _normalized_semantic_shape(ROOT / "examples" / "parity" / "python" / "basic.py")
    typescript_shape = _normalized_semantic_shape(ROOT / "examples" / "parity" / "typescript" / "basic.ts")

    assert python_shape["module_id"] == typescript_shape["module_id"] == "demo.parity"
    assert python_shape["block_count"] == typescript_shape["block_count"] == 4
    assert python_shape["blocks"] == typescript_shape["blocks"]


def test_python_typescript_and_go_parity_fixtures_match_minimal_common_shape() -> None:
    python_shape = _minimal_common_shape(ROOT / "examples" / "parity" / "python" / "basic.py")
    typescript_shape = _minimal_common_shape(ROOT / "examples" / "parity" / "typescript" / "basic.ts")
    go_shape = _minimal_common_shape(ROOT / "examples" / "parity" / "go" / "basic.go")

    assert python_shape["module_id"] == typescript_shape["module_id"] == go_shape["module_id"] == "demo.parity"
    assert python_shape["block_count"] == typescript_shape["block_count"] == go_shape["block_count"] == 4
    assert python_shape["blocks"] == typescript_shape["blocks"] == go_shape["blocks"]


def test_parity_fixtures_preserve_expected_anchor_order() -> None:
    python_shape = _normalized_semantic_shape(ROOT / "examples" / "parity" / "python" / "basic.py")

    assert [block["anchor_id"] for block in python_shape["blocks"]] == [
        "demo.parity.example",
        "demo.parity.load_example",
        "demo.parity.ExampleService",
        "demo.parity.ExampleService.run",
    ]
