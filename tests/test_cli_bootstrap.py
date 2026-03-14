from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def writable_dir(tmp_path: Path, name: str) -> Path:
    target = tmp_path.parent / f"{tmp_path.name}_{name}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_cli_bootstrap_preview_is_default(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "cli_bootstrap_preview")
    source_path = write_text(
        workspace / "module.py",
        "def run() -> int:\n    return 1\n",
    )

    result = subprocess.run(
        [sys.executable, "-m", "grace.cli", "bootstrap", str(source_path)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Bootstrap preview" in result.stdout
    assert source_path.read_text(encoding="utf-8").startswith("def run")


def test_cli_bootstrap_apply_json_writes_file(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "cli_bootstrap_apply")
    source_path = write_text(
        workspace / "module.py",
        "def run() -> int:\n    return 1\n",
    )

    result = subprocess.run(
        [sys.executable, "-m", "grace.cli", "bootstrap", str(source_path), "--apply", "--json"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "bootstrap"
    assert payload["apply"] is True
    expected_module_id = f"{workspace.name}.module"
    expected_anchor_id = f"{workspace.name}.module.run"
    assert payload["files"][0]["generated_anchor_ids"] == [expected_anchor_id]
    assert f"@grace.module {expected_module_id}" in source_path.read_text(encoding="utf-8")
