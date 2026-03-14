from pathlib import Path

from grace.bootstrap_safety import evaluate_bootstrap_safety


def writable_dir(tmp_path: Path, name: str) -> Path:
    path = (tmp_path.parent / f"{tmp_path.name}_{name}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path.resolve()


def test_bootstrap_safety_reports_safe_and_unsupported_files(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "bootstrap_safety")
    write_text(workspace / "service.py", "def run() -> int:\n    return 1\n")
    json_path = write_text(workspace / "config.json", "{\"enabled\": true}\n")

    report = evaluate_bootstrap_safety(workspace)

    assert report.file_count == 2
    assert report.safe_file_count == 1
    assert report.safe_to_apply is False
    assert report.verdict_counts == {"safe_apply": 1, "unsupported": 1}
    assert [issue.path for issue in report.issues] == [json_path]
    assert report.issue_counts == {"unsupported": 1}


def test_bootstrap_safety_reports_all_safe_for_supported_scope(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "bootstrap_safety_safe")
    write_text(workspace / "service.py", "def run() -> int:\n    return 1\n")
    write_text(workspace / "App.tsx", "export const App = () => <div />;\n")

    report = evaluate_bootstrap_safety(workspace)

    assert report.file_count == 2
    assert report.safe_file_count == 2
    assert report.safe_to_apply is True
    assert report.issue_counts == {}
