from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def writable_dir(tmp_path: Path, name: str) -> Path:
    path = (tmp_path.parent / f"{tmp_path.name}_{name}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path.resolve()


def test_cli_adapter_safety_json_reports_bootstrap_readiness(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "cli_bootstrap_safety")
    write_text(workspace / "service.py", "def run() -> int:\n    return 1\n")
    write_text(workspace / "config.json", "{\"enabled\": true}\n")

    result = subprocess.run(
        [sys.executable, "-m", "grace.cli", "adapter", "safety", str(workspace), "--json"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["action"] == "safety"
    assert payload["file_count"] == 2
    assert payload["safe_file_count"] == 1
    assert payload["safe_to_apply"] is False
    assert payload["issue_counts"] == {"unsupported": 1}
