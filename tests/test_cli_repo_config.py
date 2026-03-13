from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from grace.cli import app


def _write_file(base_dir: Path, relative_path: str, content: str) -> None:
    path = base_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_cli_root_validate_uses_pyproject_grace_excludes(tmp_path: Path) -> None:
    repo_dir = tmp_path.parent / f"{tmp_path.name}_repo_config_cli"
    repo_dir.mkdir(parents=True, exist_ok=True)
    _write_file(
        repo_dir,
        "pyproject.toml",
        "[tool.grace]\nexclude = [\"examples/parity/**\"]\n",
        )
    _write_file(
        repo_dir,
        "src/alpha.py",
        "\n".join(
            [
                "# @grace.module demo.alpha",
                "# @grace.purpose Root module.",
                "# @grace.interfaces entry()",
                "# @grace.invariant Stable test fixture.",
                "",
                "# @grace.anchor demo.alpha.entry",
                "# @grace.complexity 1",
                "def entry() -> int:",
                "    return 1",
                "",
            ]
        ),
    )
    _write_file(
        repo_dir,
        "examples/parity/python/basic.py",
        "\n".join(
            [
                "# @grace.module demo.alpha",
                "# @grace.purpose Excluded parity module.",
                "# @grace.interfaces entry()",
                "# @grace.invariant Stable parity fixture.",
                "",
                "# @grace.anchor demo.alpha.entry",
                "# @grace.complexity 1",
                "def entry() -> int:",
                "    return 2",
                "",
            ]
        ),
    )

    runner = CliRunner()
    previous_cwd = Path.cwd()
    os.chdir(repo_dir)
    try:
        validate_result = runner.invoke(app, ["validate", "--json", "."], catch_exceptions=False)
        assert validate_result.exit_code == 0
        validate_payload = json.loads(validate_result.output)
        assert validate_payload["ok"] is True

        map_result = runner.invoke(app, ["map", "--json", "."], catch_exceptions=False)
        assert map_result.exit_code == 0
        map_payload = json.loads(map_result.output)
        assert len(map_payload["modules"]) == 1

        explicit_result = runner.invoke(app, ["parse", "--json", "examples/parity/python"], catch_exceptions=False)
        assert explicit_result.exit_code == 0
        explicit_payload = json.loads(explicit_result.output)
        assert explicit_payload["file_count"] == 1
    finally:
        os.chdir(previous_cwd)
