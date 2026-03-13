from __future__ import annotations

import importlib.util
import sys
import textwrap
import types
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_modules():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.language_adapter",
        "grace.python_adapter",
        "grace.map",
        "grace.query",
        "grace.path_query",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "map", "query", "path_query"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module
    return loaded["parser"], loaded["map"], loaded["path_query"]


PARSER, MAP, PATH_QUERY = load_modules()


def write_temp_python_file(tmp_path: Path, content: str, name: str) -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_query_path"
    writable_dir.mkdir(parents=True, exist_ok=True)
    path = writable_dir / name
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def module_header(module_id: str, interfaces: str) -> str:
    return (
        f"# @grace.module {module_id}\n"
        "# @grace.purpose Deterministic query-path test fixture.\n"
        f"# @grace.interfaces {interfaces}\n"
        "# @grace.invariant Semantic paths remain deterministic.\n"
    )


def function_block(anchor: str, signature: str, body: str, *, links: str | None = None) -> str:
    lines = [f"# @grace.anchor {anchor}", "# @grace.complexity 1"]
    if links is not None:
        lines.append(f"# @grace.links {links}")
    lines.extend([signature, body])
    return "\n".join(lines)


def parse_file(tmp_path: Path, name: str, content: str):
    return PARSER.parse_python_file(write_temp_python_file(tmp_path, content, name))


def build_map(tmp_path: Path):
    alpha = parse_file(
        tmp_path,
        "alpha.py",
        "\n\n".join(
            [
                module_header("demo.alpha", "entry()"),
                function_block("demo.alpha.entry", "def entry() -> int:", "    return 1", links="demo.beta.middle,demo.gamma.side"),
            ]
        ),
    )
    beta = parse_file(
        tmp_path,
        "beta.py",
        "\n\n".join(
            [
                module_header("demo.beta", "middle()"),
                function_block("demo.beta.middle", "def middle() -> int:", "    return 2", links="demo.delta.target"),
            ]
        ),
    )
    gamma = parse_file(
        tmp_path,
        "gamma.py",
        "\n\n".join(
            [
                module_header("demo.gamma", "side()"),
                function_block("demo.gamma.side", "def side() -> int:", "    return 3"),
            ]
        ),
    )
    delta = parse_file(
        tmp_path,
        "delta.py",
        "\n\n".join(
            [
                module_header("demo.delta", "target()"),
                function_block("demo.delta.target", "def target() -> int:", "    return 4"),
            ]
        ),
    )
    return MAP.build_project_map([alpha, beta, gamma, delta])


def test_query_path_returns_deterministic_shortest_path(tmp_path: Path) -> None:
    grace_map = build_map(tmp_path)

    path = PATH_QUERY.query_path(grace_map, "demo.alpha.entry", "demo.delta.target")

    assert [anchor.anchor_id for anchor in path] == [
        "demo.alpha.entry",
        "demo.beta.middle",
        "demo.delta.target",
    ]
    assert PATH_QUERY.query_path_edge_types(path) == (
        "anchor_links_to_anchor",
        "anchor_links_to_anchor",
    )


def test_query_path_returns_empty_tuple_when_no_directed_path_exists(tmp_path: Path) -> None:
    grace_map = build_map(tmp_path)

    path = PATH_QUERY.query_path(grace_map, "demo.gamma.side", "demo.delta.target")

    assert path == ()
    assert PATH_QUERY.query_path_edge_types(path) == ()


def test_query_path_self_target_returns_single_anchor(tmp_path: Path) -> None:
    grace_map = build_map(tmp_path)

    path = PATH_QUERY.query_path(grace_map, "demo.beta.middle", "demo.beta.middle")

    assert [anchor.anchor_id for anchor in path] == ["demo.beta.middle"]
