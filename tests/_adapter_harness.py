from __future__ import annotations

import textwrap
from pathlib import Path

from grace.parser import parse_python_file


ROOT = Path(__file__).resolve().parents[1]

ADAPTER_CASES = (
    {
        "language": "python",
        "class_name": "PythonAdapter",
        "parity_basic": ROOT / "examples" / "parity" / "python" / "basic.py",
    },
    {
        "language": "typescript",
        "class_name": "TypeScriptAdapter",
        "parity_basic": ROOT / "examples" / "parity" / "typescript" / "basic.ts",
    },
    {
        "language": "go",
        "class_name": "GoAdapter",
        "parity_basic": ROOT / "examples" / "parity" / "go" / "basic.go",
    },
)

PARITY_GROUPS = (
    (
        ROOT / "examples" / "parity" / "python" / "basic.py",
        ROOT / "examples" / "parity" / "typescript" / "basic.ts",
        ROOT / "examples" / "parity" / "go" / "basic.go",
    ),
    (
        ROOT / "examples" / "parity" / "python" / "async_shape.py",
        ROOT / "examples" / "parity" / "typescript" / "async_shape.ts",
        ROOT / "examples" / "parity" / "go" / "async_shape.go",
    ),
    (
        ROOT / "examples" / "parity" / "python" / "service_shape.py",
        ROOT / "examples" / "parity" / "typescript" / "service_shape.ts",
        ROOT / "examples" / "parity" / "go" / "service_shape.go",
    ),
    (
        ROOT / "examples" / "parity" / "python" / "links_shape.py",
        ROOT / "examples" / "parity" / "typescript" / "links_shape.ts",
        ROOT / "examples" / "parity" / "go" / "links_shape.go",
    ),
)


def normalized_semantic_shape(path: Path) -> dict[str, object]:
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


def minimal_common_shape(path: Path) -> dict[str, object]:
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


def write_adapter_fixture(tmp_path: Path, suffix: str, content: str) -> Path:
    fixture_dir = tmp_path.parent / f"{tmp_path.name}_adapter_harness_files"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    path = fixture_dir / suffix
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path
