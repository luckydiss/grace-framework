from __future__ import annotations

import textwrap

from grace.models import ParseErrorCode
from grace.parser import parse_python_file
from tests._adapter_harness import PARITY_GROUPS, ROOT, minimal_common_shape, normalized_semantic_shape, write_adapter_fixture


def _adapter_eval_metrics(tmp_path: Path) -> dict[str, float]:
    expected_failure_code = ParseErrorCode.ARBITRARY_CODE_BETWEEN_ANNOTATIONS_AND_BLOCK.value
    parse_targets = (
        ROOT / "examples" / "parity" / "python" / "basic.py",
        ROOT / "examples" / "parity" / "python" / "async_shape.py",
        ROOT / "examples" / "parity" / "python" / "service_shape.py",
        ROOT / "examples" / "parity" / "python" / "links_shape.py",
        ROOT / "examples" / "parity" / "typescript" / "basic.ts",
        ROOT / "examples" / "parity" / "typescript" / "async_shape.ts",
        ROOT / "examples" / "parity" / "typescript" / "service_shape.ts",
        ROOT / "examples" / "parity" / "typescript" / "links_shape.ts",
        ROOT / "examples" / "parity" / "go" / "basic.go",
        ROOT / "examples" / "parity" / "go" / "async_shape.go",
        ROOT / "examples" / "parity" / "go" / "service_shape.go",
        ROOT / "examples" / "parity" / "go" / "links_shape.go",
    )

    parse_successes = 0
    deterministic_successes = 0
    for path in parse_targets:
        first = parse_python_file(path)
        second = parse_python_file(path)
        parse_successes += 1
        deterministic_successes += int(first.model_dump(mode="python") == second.model_dump(mode="python"))

    parity_successes = 0
    for paths in PARITY_GROUPS:
        shapes = [minimal_common_shape(path) for path in paths]
        parity_successes += int(shapes[0] == shapes[1] == shapes[2])

        unsupported_cases = (
            (
                write_adapter_fixture(
                    tmp_path,
                    "python_inert.py",
                """
                # @grace.module demo.eval.python_inert
                # @grace.purpose Python inert unsupported syntax fixture.
                # @grace.interfaces stable() -> int
                # @grace.invariant Unsupported syntax without anchors must stay inert.

                value = lambda: 1

                # @grace.anchor demo.eval.python_inert.stable
                # @grace.complexity 1
                def stable() -> int:
                    return 1
                """,
            ),
            True,
            ),
            (
                write_adapter_fixture(
                    tmp_path,
                    "python_invalid.py",
                """
                # @grace.module demo.eval.python_invalid
                # @grace.purpose Python invalid unsupported syntax fixture.
                # @grace.interfaces broken() -> int
                # @grace.invariant Unsupported annotated syntax must fail predictably.

                # @grace.anchor demo.eval.python_invalid.broken
                # @grace.complexity 1
                value = lambda: 1
                """,
            ),
            False,
            ),
            (
                write_adapter_fixture(
                    tmp_path,
                    "typescript_inert.ts",
                """
                // @grace.module demo.eval.typescript_inert
                // @grace.purpose TypeScript inert unsupported syntax fixture.
                // @grace.interfaces stable(): number
                // @grace.invariant Unsupported syntax without anchors must stay inert.

                const helper = function (): number {
                  return 1;
                };

                // @grace.anchor demo.eval.typescript_inert.stable
                // @grace.complexity 1
                function stable(): number {
                  return 1;
                }
                """,
            ),
            True,
            ),
            (
                write_adapter_fixture(
                    tmp_path,
                    "typescript_invalid.ts",
                """
                // @grace.module demo.eval.typescript_invalid
                // @grace.purpose TypeScript invalid unsupported syntax fixture.
                // @grace.interfaces broken(): number
                // @grace.invariant Unsupported annotated syntax must fail predictably.

                // @grace.anchor demo.eval.typescript_invalid.broken
                // @grace.complexity 1
                const broken = function (): number {
                  return 1;
                };
                """,
            ),
            False,
            ),
            (
                write_adapter_fixture(
                    tmp_path,
                    "go_inert.go",
                """
                // @grace.module demo.eval.go_inert
                // @grace.purpose Go inert unsupported syntax fixture.
                // @grace.interfaces stable() int
                // @grace.invariant Unsupported syntax without anchors must stay inert.

                type Helper interface {
                    Run() int
                }

                // @grace.anchor demo.eval.go_inert.stable
                // @grace.complexity 1
                func stable() int {
                    return 1
                }
                """,
            ),
            True,
            ),
            (
                write_adapter_fixture(
                    tmp_path,
                    "go_invalid.go",
                """
                // @grace.module demo.eval.go_invalid
                // @grace.purpose Go invalid unsupported syntax fixture.
                // @grace.interfaces broken() int
                // @grace.invariant Unsupported annotated syntax must fail predictably.

                // @grace.anchor demo.eval.go_invalid.broken
                // @grace.complexity 1
                type Broken interface {
                    Run() int
                }
                """,
            ),
            False,
        ),
    )

    unsupported_matches = 0
    for path, should_pass in unsupported_cases:
        try:
            parse_python_file(path)
            unsupported_matches += int(should_pass)
        except Exception as exc:
            unsupported_matches += int(
                (not should_pass)
                and type(exc).__name__ == "GraceParseError"
                and any(issue.code.value == expected_failure_code for issue in exc.errors)
            )

    case_count = len(unsupported_cases)
    parse_count = len(parse_targets)
    parity_count = len(PARITY_GROUPS)
    return {
        "adapter_parse_success_rate": parse_successes / parse_count,
        "semantic_parity_rate": parity_successes / parity_count,
        "deterministic_parse_rate": deterministic_successes / parse_count,
        "unsupported_syntax_failure_precision": unsupported_matches / case_count,
    }


def test_adapter_eval_metrics_are_stable(tmp_path: Path) -> None:
    metrics = _adapter_eval_metrics(tmp_path)

    assert metrics == {
        "adapter_parse_success_rate": 1.0,
        "semantic_parity_rate": 1.0,
        "deterministic_parse_rate": 1.0,
        "unsupported_syntax_failure_precision": 1.0,
    }


def test_basic_python_and_typescript_fixtures_preserve_strict_shape() -> None:
    python_shape = normalized_semantic_shape(ROOT / "examples" / "parity" / "python" / "basic.py")
    typescript_shape = normalized_semantic_shape(ROOT / "examples" / "parity" / "typescript" / "basic.ts")

    assert python_shape["blocks"] == typescript_shape["blocks"]
