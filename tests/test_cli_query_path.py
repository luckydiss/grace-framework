from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
import types
from functools import lru_cache
from pathlib import Path

from click.testing import CliRunner


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_cli_modules():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.language_adapter",
        "grace.python_adapter",
        "grace.validator",
        "grace.linter",
        "grace.map",
        "grace.query",
        "grace.path_query",
        "grace.cli",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "validator", "linter", "map", "query", "path_query", "cli"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module
    return loaded["cli"]


CLI = load_cli_modules()


def runner() -> CliRunner:
    return CliRunner()


def write_file(repo_dir: Path, relative_path: str, content: str) -> Path:
    path = repo_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def build_repo(tmp_path: Path) -> Path:
    repo_dir = tmp_path.parent / f"{tmp_path.name}_cli_query_path"
    repo_dir.mkdir(parents=True, exist_ok=True)
    write_file(
        repo_dir,
        "alpha.py",
        """
        # @grace.module demo.alpha
        # @grace.purpose Path query fixture.
        # @grace.interfaces entry()
        # @grace.invariant Path ordering is deterministic.

        # @grace.anchor demo.alpha.entry
        # @grace.complexity 1
        # @grace.links demo.beta.middle,demo.gamma.side
        def entry() -> int:
            return 1
        """,
    )
    write_file(
        repo_dir,
        "beta.py",
        """
        # @grace.module demo.beta
        # @grace.purpose Path query fixture.
        # @grace.interfaces middle()
        # @grace.invariant Path ordering is deterministic.

        # @grace.anchor demo.beta.middle
        # @grace.complexity 1
        # @grace.links demo.delta.target
        def middle() -> int:
            return 2
        """,
    )
    write_file(
        repo_dir,
        "gamma.py",
        """
        # @grace.module demo.gamma
        # @grace.purpose Path query fixture.
        # @grace.interfaces side()
        # @grace.invariant Path ordering is deterministic.

        # @grace.anchor demo.gamma.side
        # @grace.complexity 1
        def side() -> int:
            return 3
        """,
    )
    write_file(
        repo_dir,
        "delta.py",
        """
        # @grace.module demo.delta
        # @grace.purpose Path query fixture.
        # @grace.interfaces target()
        # @grace.invariant Path ordering is deterministic.

        # @grace.anchor demo.delta.target
        # @grace.complexity 1
        def target() -> int:
            return 4
        """,
    )
    return repo_dir


def test_cli_query_path_returns_shortest_path_json(tmp_path: Path) -> None:
    repo_dir = build_repo(tmp_path)

    result = runner().invoke(CLI.app, ["query", "path", "--json", str(repo_dir), "demo.alpha.entry", "demo.delta.target"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "query"
    assert payload["query"] == "path"
    assert payload["query_scope"] == "anchor"
    assert payload["found"] is True
    assert payload["source_anchor_id"] == "demo.alpha.entry"
    assert payload["target_anchor_id"] == "demo.delta.target"
    assert payload["edge_types"] == [
        "anchor_links_to_anchor",
        "anchor_links_to_anchor",
    ]
    assert [anchor["anchor_id"] for anchor in payload["route"]] == [
        "demo.alpha.entry",
        "demo.beta.middle",
        "demo.delta.target",
    ]


def test_cli_query_path_returns_not_found_payload_when_no_directed_path_exists(tmp_path: Path) -> None:
    repo_dir = build_repo(tmp_path)

    result = runner().invoke(CLI.app, ["query", "path", "--json", str(repo_dir), "demo.gamma.side", "demo.delta.target"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["found"] is False
    assert payload["route"] == []
    assert payload["edge_types"] == []


def test_cli_query_path_unknown_anchor_has_stable_failure(tmp_path: Path) -> None:
    repo_dir = build_repo(tmp_path)

    result = runner().invoke(CLI.app, ["query", "path", "--json", str(repo_dir), "demo.alpha.entry", "demo.missing.anchor"])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "query"
    assert payload["query"] == "path"
    assert payload["query_scope"] == "anchor"
    assert payload["stage"] == "query"
    # Target anchor is carried in the generic anchor_id slot for lookup failures.
    assert payload["anchor_id"] == "demo.missing.anchor"
