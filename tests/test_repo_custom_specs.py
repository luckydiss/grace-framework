from pathlib import Path

from grace.spec_loader import load_language_pack_for_path, load_repo_spec_paths


def writable_dir(tmp_path: Path, name: str) -> Path:
    target = (tmp_path.parent / f"{tmp_path.name}_{name}").resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_repo_local_language_specs_override_core(tmp_path: Path) -> None:
    repo_root = writable_dir(tmp_path, "repo_custom_specs")
    language_dir = repo_root / ".grace" / "specs" / "languages"
    language_dir.mkdir(parents=True)
    sample_path = repo_root / "demo.mini"
    sample_path.write_text("def demo():\n    return 1\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[tool.grace]",
                'include = ["**/*"]',
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (language_dir / "mini.toml").write_text(
        "\n".join(
            [
                'language_name = "mini"',
                'file_extensions = [".mini"]',
                'status = "experimental"',
                'line_comment_prefixes = ["#"]',
                "",
                "[grammar]",
                'provider = "python_callable"',
                'target = "tree_sitter_python:language"',
                "",
                "[[queries]]",
                'query = "(module (function_definition name: (identifier) @name) @block)"',
                'kind = "function"',
                'symbol_capture = "name"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    pack = load_language_pack_for_path(sample_path)

    assert pack is not None
    assert pack.language_name == "mini"
    assert pack.primary_extension == ".mini"
    assert load_repo_spec_paths(sample_path) == (language_dir,)


def test_repo_configured_language_spec_dirs_are_loaded(tmp_path: Path) -> None:
    repo_root = writable_dir(tmp_path, "repo_custom_spec_dirs")
    language_dir = repo_root / "custom_specs" / "languages"
    language_dir.mkdir(parents=True)
    sample_path = repo_root / "demo.altpy"
    sample_path.write_text("def demo():\n    return 1\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[tool.grace]",
                "",
                "[tool.grace.specs]",
                'language_dirs = ["custom_specs/languages"]',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (language_dir / "alt.toml").write_text(
        "\n".join(
            [
                'language_name = "alt-python"',
                'file_extensions = [".altpy"]',
                'status = "experimental"',
                'line_comment_prefixes = ["#"]',
                "",
                "[grammar]",
                'provider = "python_callable"',
                'target = "tree_sitter_python:language"',
                "",
                "[[queries]]",
                'query = "(module (function_definition name: (identifier) @name) @block)"',
                'kind = "function"',
                'symbol_capture = "name"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    pack = load_language_pack_for_path(sample_path)

    assert pack is not None
    assert pack.language_name == "alt-python"
    assert pack.primary_extension == ".altpy"
    assert load_repo_spec_paths(sample_path) == (language_dir,)
