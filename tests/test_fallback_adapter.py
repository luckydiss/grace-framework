from pathlib import Path

import pytest

from grace.fallback_adapter import FallbackTextAdapter
from grace.language_adapter import get_language_adapter_for_path
from grace.models import BlockKind
from grace.parser import GraceParseError


def write_text_file(tmp_path: Path, name: str, content: str) -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_fallback_files"
    writable_dir.mkdir(parents=True, exist_ok=True)
    try:
        writable_dir.chmod(0o777)
    except OSError:
        pass
    path = writable_dir / name
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def test_unknown_suffix_routes_to_fallback_adapter(tmp_path: Path) -> None:
    source_path = write_text_file(
        tmp_path,
        "script.sh",
        """
        # @grace.module demo.shell
        # @grace.purpose Demo shell module.
        # @grace.interfaces run()
        # @grace.invariant The shell fallback stays deterministic.

        # @grace.anchor demo.shell.run
        # @grace.complexity 1
        run() {
            echo ok
        }
        """,
    )

    adapter = get_language_adapter_for_path(source_path)
    assert isinstance(adapter, FallbackTextAdapter)
    parsed = adapter.build_grace_file_model(source_path)

    assert parsed.module.module_id == "demo.shell"
    assert len(parsed.blocks) == 1
    assert parsed.blocks[0].kind.value == BlockKind.FUNCTION.value


def test_fallback_adapter_reports_invalid_binding_predictably(tmp_path: Path) -> None:
    from grace import parser as parser_module

    source_path = write_text_file(
        tmp_path,
        "broken.md",
        """
        # @grace.module demo.markdown
        # @grace.purpose Broken module.
        # @grace.interfaces heading()
        # @grace.invariant Must fail when no bindable block follows.

        # @grace.anchor demo.markdown.heading
        # @grace.complexity 1
        plain text only
        """,
    )

    with pytest.raises(parser_module.GraceParseError):
        FallbackTextAdapter().build_grace_file_model(source_path)
