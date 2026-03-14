from pathlib import Path

from grace.grammar_manager import (
    GrammarInstallRecord,
    install_grammar_record,
    list_installed_grammars,
    load_installed_grammar_record,
)


def writable_dir(tmp_path: Path, name: str) -> Path:
    target = (tmp_path.parent / f"{tmp_path.name}_{name}").resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_install_and_load_python_callable_grammar_record(tmp_path: Path) -> None:
    repo_root = writable_dir(tmp_path, "grammar_manager")
    (repo_root / "pyproject.toml").write_text("[tool.grace]\n", encoding="utf-8")

    record = GrammarInstallRecord(
        language_name="python-alt",
        provider="python_callable",
        target="tree_sitter_python:language",
    )
    install_grammar_record(record, repo_root)

    loaded = load_installed_grammar_record("python-alt", repo_root)
    records = list_installed_grammars(repo_root)

    assert loaded == record
    assert records == (record,)
