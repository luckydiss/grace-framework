from __future__ import annotations

from pathlib import Path

from grace.repo_config import GraceRepoConfig, candidate_in_repo_scope, load_repo_config


def test_load_repo_config_reads_file_policy_overrides(tmp_path: Path) -> None:
    repo_dir = tmp_path.parent / f"{tmp_path.name}_repo_file_policy"
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "pyproject.toml").write_text(
        "\n".join(
            [
                "[tool.grace]",
                'include = ["src/**"]',
                "",
                "[tool.grace.file_policy]",
                'preview_only = ["src/**/*.tsx"]',
                'unsupported = ["src/**/*.json"]',
                'generated = ["src/generated/**"]',
                'ignore = ["vendor/**"]',
                "",
            ]
        ),
        encoding="utf-8",
    )
    nested_dir = repo_dir / "src"
    nested_dir.mkdir()

    config = load_repo_config(nested_dir)

    assert isinstance(config, GraceRepoConfig)
    assert config.preview_only == ("src/**/*.tsx",)
    assert config.unsupported == ("src/**/*.json",)
    assert config.generated == ("src/generated/**",)
    assert config.ignore == ("vendor/**",)


def test_candidate_in_repo_scope_excludes_generated_patterns_at_root() -> None:
    repo_root = Path("C:/repo").resolve()
    config = GraceRepoConfig(
        root=repo_root,
        include=("src/**",),
        generated=("src/generated/**",),
    )

    generated_candidate = repo_root / "src" / "generated" / "client.py"
    normal_candidate = repo_root / "src" / "billing.py"

    assert candidate_in_repo_scope(config, repo_root, normal_candidate) is True
    assert candidate_in_repo_scope(config, repo_root, generated_candidate) is False
