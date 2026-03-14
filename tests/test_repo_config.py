from __future__ import annotations

from pathlib import Path

from grace.repo_config import GraceRepoConfig, candidate_in_repo_scope, load_repo_config


def test_load_repo_config_reads_tool_grace_from_nearest_pyproject(tmp_path: Path) -> None:
    repo_dir = tmp_path.parent / f"{tmp_path.name}_repo_config"
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "pyproject.toml").write_text(
        "\n".join(
            [
                "[tool.grace]",
                'include = ["grace/**"]',
                'exclude = ["examples/parity/**"]',
                "",
                "[tool.grace.specs]",
                'language_dirs = ["custom/languages"]',
                'construct_dirs = ["custom/constructs"]',
                "",
                "[tool.grace.grammar]",
                'cache_dir = ".cache/grammars"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    nested_dir = repo_dir / "grace"
    nested_dir.mkdir()

    config = load_repo_config(nested_dir)

    assert isinstance(config, GraceRepoConfig)
    assert config.root == repo_dir.resolve()
    assert config.include == ("grace/**",)
    assert config.exclude == ("examples/parity/**",)
    assert config.language_spec_dirs == ("custom/languages",)
    assert config.construct_spec_dirs == ("custom/constructs",)
    assert config.grammar_cache_dir == ".cache/grammars"


def test_candidate_in_repo_scope_applies_exclude_at_repo_root_only() -> None:
    repo_root = Path("C:/repo").resolve()
    config = GraceRepoConfig(root=repo_root, exclude=("examples/parity/**",))
    excluded_candidate = repo_root / "examples" / "parity" / "python" / "basic.py"

    assert candidate_in_repo_scope(config, repo_root, excluded_candidate) is False
    assert candidate_in_repo_scope(config, repo_root / "examples" / "parity" / "python", excluded_candidate) is True
