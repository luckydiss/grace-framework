from __future__ import annotations

from pathlib import Path

from grace.adapter_tools import collect_adapter_gaps, evaluate_adapter_surface, probe_adapter


def writable_dir(tmp_path: Path, name: str) -> Path:
    target = tmp_path.parent / f"{tmp_path.name}_{name}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_probe_adapter_reports_pack_and_policy_for_python_file(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "adapter_probe_python")
    source_path = write_text(workspace / "service.py", "def run() -> int:\n    return 1\n")

    probe = probe_adapter(source_path)

    assert probe.language_name == "python"
    assert probe.policy_verdict == "safe_apply"
    assert probe.adapter_class_name == "PythonAdapter"


def test_probe_adapter_reports_preview_only_for_tsx(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "adapter_probe_tsx")
    source_path = write_text(workspace / "App.tsx", "export const App = () => <div />;\n")

    probe = probe_adapter(source_path)

    assert probe.language_name is None
    assert probe.policy_verdict == "preview_only"
    assert probe.file_class == "code"


def test_collect_adapter_gaps_returns_only_non_green_files(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "adapter_gaps")
    write_text(workspace / "service.py", "def run() -> int:\n    return 1\n")
    tsx_path = write_text(workspace / "App.tsx", "export const App = () => <div />;\n")
    json_path = write_text(workspace / "config.json", "{\"enabled\": true}\n")

    gaps = collect_adapter_gaps(workspace)

    assert [gap.path for gap in gaps] == [tsx_path.resolve(), json_path.resolve()]
    assert [gap.gap_kind for gap in gaps] == ["preview_only", "unsupported"]


def test_evaluate_adapter_surface_summarizes_repository_policy(tmp_path: Path) -> None:
    workspace = writable_dir(tmp_path, "adapter_eval")
    write_text(workspace / "service.py", "def run() -> int:\n    return 1\n")
    write_text(workspace / "App.tsx", "export const App = () => <div />;\n")
    write_text(workspace / "config.json", "{\"enabled\": true}\n")

    summary = evaluate_adapter_surface(workspace)

    assert summary.file_count == 3
    assert summary.verdict_counts == {
        "preview_only": 1,
        "safe_apply": 1,
        "unsupported": 1,
    }
    assert summary.gap_counts == {
        "preview_only": 1,
        "unsupported": 1,
    }
