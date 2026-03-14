from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def writable_dir(tmp_path: Path, name: str) -> Path:
    target = tmp_path.parent / f"{tmp_path.name}_{name}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_cli_adapter_probe_json_reports_python_file(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "cli_adapter_probe")
    source_path = write_text(workspace / "service.py", "def run() -> int:\n    return 1\n")

    result = subprocess.run(
        [sys.executable, "-m", "grace.cli", "adapter", "probe", str(source_path), "--json"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "adapter"
    assert payload["action"] == "probe"
    assert payload["language_name"] == "python"
    assert payload["policy_verdict"] == "safe_apply"


def test_cli_adapter_gaps_json_reports_non_green_files(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "cli_adapter_gaps")
    write_text(workspace / "service.py", "def run() -> int:\n    return 1\n")
    write_text(workspace / "App.tsx", "export const App = () => <div />;\n")
    write_text(workspace / "config.json", "{\"enabled\": true}\n")

    result = subprocess.run(
        [sys.executable, "-m", "grace.cli", "adapter", "gaps", str(workspace), "--json"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["action"] == "gaps"
    assert payload["gap_count"] == 2
    assert [gap["gap_kind"] for gap in payload["gaps"]] == ["preview_only", "unsupported"]


def test_cli_adapter_eval_json_summarizes_scope(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "cli_adapter_eval")
    write_text(workspace / "service.py", "def run() -> int:\n    return 1\n")
    write_text(workspace / "App.tsx", "export const App = () => <div />;\n")
    write_text(workspace / "config.json", "{\"enabled\": true}\n")

    result = subprocess.run(
        [sys.executable, "-m", "grace.cli", "adapter", "eval", str(workspace), "--json"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["action"] == "eval"
    assert payload["file_count"] == 3
    assert payload["verdict_counts"] == {
        "preview_only": 1,
        "safe_apply": 1,
        "unsupported": 1,
    }
