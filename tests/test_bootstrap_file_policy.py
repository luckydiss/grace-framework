from __future__ import annotations

from pathlib import Path

from grace.bootstrapper import BootstrapFailure, BootstrapFailureStage, BootstrapSuccess, bootstrap_path


def writable_dir(tmp_path: Path, name: str) -> Path:
    target = tmp_path.parent / f"{tmp_path.name}_{name}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_bootstrap_rejects_unsupported_json_file(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "bootstrap_policy_json")
    source_path = _write(workspace / "en.json", "{\"hello\": \"world\"}\n")

    result = bootstrap_path(source_path)

    assert isinstance(result, BootstrapFailure)
    assert result.stage is BootstrapFailureStage.DISCOVERY
    assert "not safe for GRACE bootstrap" in result.message


def test_bootstrap_directory_skips_unsupported_files(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "bootstrap_policy_dir")
    python_file = _write(workspace / "service.py", "def run() -> int:\n    return 1\n")
    _write(workspace / "config.json", "{\"enabled\": true}\n")

    result = bootstrap_path(workspace)

    assert isinstance(result, BootstrapSuccess)
    assert [change.path for change in result.file_changes] == [python_file.resolve()]
