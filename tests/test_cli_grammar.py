import json
import subprocess
import sys
from pathlib import Path


def writable_dir(tmp_path: Path, name: str) -> Path:
    target = (tmp_path.parent / f"{tmp_path.name}_{name}").resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target


def _run_cli(*args: str, cwd: Path) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-m", "grace.cli", *args, "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def test_cli_grammar_install_and_list(tmp_path: Path) -> None:
    repo_root = writable_dir(tmp_path, "cli_grammar")
    (repo_root / "pyproject.toml").write_text("[tool.grace]\n", encoding="utf-8")

    install_payload = _run_cli(
        "grammar",
        "install",
        "python-alt",
        str(repo_root),
        "--callable-target",
        "tree_sitter_python:language",
        cwd=repo_root,
    )
    list_payload = _run_cli("grammar", "list", str(repo_root), cwd=repo_root)

    assert install_payload["ok"] is True
    assert list_payload["ok"] is True
    assert list_payload["count"] == 1
