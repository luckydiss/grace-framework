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
        "grace.go_adapter",
        "grace.tree_sitter_adapter",
        "grace.typescript_adapter",
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
        "go_adapter",
        "tree_sitter_adapter",
        "typescript_adapter",
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
        loaded["python_adapter"],
        loaded["go_adapter"],
        loaded["typescript_adapter"],
    )


MODELS, PARSER, LANGUAGE_ADAPTER, PYTHON_ADAPTER, GO_ADAPTER, TYPESCRIPT_ADAPTER = load_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER, LANGUAGE_ADAPTER, PYTHON_ADAPTER, GO_ADAPTER, TYPESCRIPT_ADAPTER
    load_modules.cache_clear()
    MODELS, PARSER, LANGUAGE_ADAPTER, PYTHON_ADAPTER, GO_ADAPTER, TYPESCRIPT_ADAPTER = load_modules()


def write_fixture_file(tmp_path: Path, name: str, content: str) -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_adapter_conformance_files"
    writable_dir.mkdir(parents=True, exist_ok=True)
    try:
        writable_dir.chmod(0o777)
    except OSError:
        pass
    path = writable_dir / name
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("path", "module_name", "class_name"),
    [
        (ROOT / "examples" / "parity" / "python" / "basic.py", "python_adapter", "PythonAdapter"),
        (ROOT / "examples" / "parity" / "typescript" / "basic.ts", "typescript_adapter", "TypeScriptAdapter"),
        (ROOT / "examples" / "parity" / "go" / "basic.go", "go_adapter", "GoAdapter"),
    ],
)
def test_adapter_registry_detects_supported_file_types(path: Path, module_name: str, class_name: str) -> None:
    adapter = LANGUAGE_ADAPTER.get_language_adapter_for_path(path)
    adapter_module = {
        "python_adapter": PYTHON_ADAPTER,
        "typescript_adapter": TYPESCRIPT_ADAPTER,
        "go_adapter": GO_ADAPTER,
    }[module_name]
    adapter_type = getattr(adapter_module, class_name)
    assert isinstance(adapter, adapter_type)


@pytest.mark.parametrize(
    "path",
    [
        ROOT / "examples" / "parity" / "python" / "basic.py",
        ROOT / "examples" / "parity" / "typescript" / "basic.ts",
        ROOT / "examples" / "parity" / "go" / "basic.go",
    ],
)
def test_adapter_build_grace_file_model_returns_grace_file_model(path: Path) -> None:
    adapter = LANGUAGE_ADAPTER.get_language_adapter_for_path(path)
    grace_file = adapter.build_grace_file_model(path)

    assert isinstance(grace_file, MODELS.GraceFileModel)
    assert grace_file.path == path


@pytest.mark.parametrize(
    "path",
    [
        ROOT / "examples" / "parity" / "python" / "basic.py",
        ROOT / "examples" / "parity" / "typescript" / "basic.ts",
        ROOT / "examples" / "parity" / "go" / "basic.go",
    ],
)
def test_adapter_output_is_deterministic(path: Path) -> None:
    adapter = LANGUAGE_ADAPTER.get_language_adapter_for_path(path)
    first = adapter.build_grace_file_model(path)
    second = adapter.build_grace_file_model(path)

    assert first.model_dump(mode="python") == second.model_dump(mode="python")


@pytest.mark.parametrize(
    "path",
    [
        ROOT / "examples" / "parity" / "python" / "basic.py",
        ROOT / "examples" / "parity" / "typescript" / "basic.ts",
        ROOT / "examples" / "parity" / "go" / "basic.go",
    ],
)
def test_adapter_block_spans_are_valid_and_monotonic(path: Path) -> None:
    adapter = LANGUAGE_ADAPTER.get_language_adapter_for_path(path)
    grace_file = adapter.build_grace_file_model(path)

    previous_start = 0
    for block in grace_file.blocks:
        line_start, line_end = adapter.compute_block_span(block)
        assert line_start == block.line_start
        assert line_end == block.line_end
        assert line_start >= previous_start
        assert line_end >= line_start
        previous_start = line_start


@pytest.mark.parametrize(
    ("path", "expected_purpose"),
    [
        (ROOT / "examples" / "parity" / "python" / "basic.py", "Verify semantic parity for the reference Python adapter."),
        (ROOT / "examples" / "parity" / "typescript" / "basic.ts", "Verify semantic parity for the pilot TypeScript adapter."),
        (ROOT / "examples" / "parity" / "go" / "basic.go", "Verify semantic parity for the pilot Go adapter."),
    ],
)
def test_adapter_extracts_module_metadata(path: Path, expected_purpose: str) -> None:
    adapter = LANGUAGE_ADAPTER.get_language_adapter_for_path(path)
    grace_file = adapter.build_grace_file_model(path)

    assert grace_file.module.module_id == "demo.parity"
    assert grace_file.module.purpose == expected_purpose
    assert len(grace_file.module.invariants) == 2


@pytest.mark.parametrize(
    ("name", "content"),
    [
        (
            "invalid.py",
            """
            # @grace.module demo.invalid
            # @grace.purpose Invalid python fixture.
            # @grace.interfaces broken()
            # @grace.invariant Invalid bindings must fail predictably.

            # @grace.anchor demo.invalid.broken
            # @grace.complexity 1
            value = 1
            """,
        ),
        (
            "invalid.ts",
            """
            // @grace.module demo.invalid
            // @grace.purpose Invalid typescript fixture.
            // @grace.interfaces broken()
            // @grace.invariant Invalid bindings must fail predictably.

            // @grace.anchor demo.invalid.broken
            // @grace.complexity 1
            const broken = () => 1;
            """,
        ),
        (
            "invalid.go",
            """
            // @grace.module demo.invalid
            // @grace.purpose Invalid go fixture.
            // @grace.interfaces broken()
            // @grace.invariant Invalid bindings must fail predictably.

            // @grace.anchor demo.invalid.broken
            // @grace.complexity 1
            type broken interface {
                Run() int
            }
            """,
        ),
    ],
)
def test_invalid_grace_files_produce_predictable_parse_failures(tmp_path: Path, name: str, content: str) -> None:
    path = write_fixture_file(tmp_path, name, content)

    with pytest.raises(Exception) as exc_info:
        PARSER.parse_python_file(path)

    parse_error = exc_info.value
    assert type(parse_error).__name__ == "GraceParseError"
    assert any(
        issue.code is MODELS.ParseErrorCode.ARBITRARY_CODE_BETWEEN_ANNOTATIONS_AND_BLOCK
        for issue in parse_error.errors
    )
