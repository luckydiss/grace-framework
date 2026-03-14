from __future__ import annotations

from pathlib import Path

from grace.file_policy import GraceFileClass, GraceFilePolicyVerdict, resolve_file_policy
from grace.repo_config import GraceRepoConfig


def writable_dir(tmp_path: Path, name: str) -> Path:
    target = tmp_path.parent / f"{tmp_path.name}_{name}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_registered_python_pack_is_safe_apply(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "file_policy_python")
    path = (workspace / "pricing.py").resolve()
    path.write_text("def run() -> int:\n    return 1\n", encoding="utf-8")

    policy = resolve_file_policy(path)

    assert policy.file_class is GraceFileClass.CODE
    assert policy.verdict is GraceFilePolicyVerdict.SAFE_APPLY
    assert policy.language_name == "python"


def test_tsx_routes_to_safe_apply_via_construct_pack(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "file_policy_tsx")
    path = (workspace / "App.tsx").resolve()
    path.write_text("export const App = () => <div />;\n", encoding="utf-8")

    policy = resolve_file_policy(path)

    assert policy.file_class is GraceFileClass.CODE
    assert policy.verdict is GraceFilePolicyVerdict.SAFE_APPLY
    assert policy.language_name == "typescript"


def test_json_defaults_to_unsupported_data_file(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "file_policy_json")
    path = (workspace / "en.json").resolve()
    path.write_text("{\"hello\": \"world\"}\n", encoding="utf-8")

    policy = resolve_file_policy(path)

    assert policy.file_class is GraceFileClass.DATA
    assert policy.verdict is GraceFilePolicyVerdict.UNSUPPORTED


def test_generated_directory_is_ignored(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "file_policy_generated")
    path = (workspace / "dist" / "bundle.js").resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("console.log('bundle');\n", encoding="utf-8")

    policy = resolve_file_policy(path)

    assert policy.file_class is GraceFileClass.GENERATED
    assert policy.verdict is GraceFilePolicyVerdict.IGNORE


def test_repo_config_overrides_builtin_policy(tmp_path: Path) -> None:
    repo_root = writable_dir(tmp_path, "file_policy_repo").resolve()
    target = repo_root / "frontend" / "src" / "App.tsx"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("export const App = () => <div />;\n", encoding="utf-8")

    config = GraceRepoConfig(
        root=repo_root,
        preview_only=("frontend/src/*.tsx",),
        unsupported=("frontend/src/*.json",),
        generated=("frontend/src/generated/**",),
        ignore=("frontend/vendor/**",),
    )

    policy = resolve_file_policy(target, config)

    assert policy.verdict is GraceFilePolicyVerdict.PREVIEW_ONLY
    assert policy.matched_pattern == "frontend/src/*.tsx"
