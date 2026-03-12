from __future__ import annotations

import _pytest.pathlib
import _pytest.tmpdir
from pathlib import Path
from uuid import uuid4


_SANDBOX_BASETEMP: Path | None = None


def pytest_configure(config) -> None:
    global _SANDBOX_BASETEMP
    basetemp_root = Path(config.rootpath) / ".tmp_parser_tests"
    basetemp_root.mkdir(exist_ok=True)
    _SANDBOX_BASETEMP = (basetemp_root / uuid4().hex).resolve()
    _SANDBOX_BASETEMP.mkdir()


def _sandbox_safe_getbasetemp(self) -> Path:
    if self._basetemp is None:
        assert _SANDBOX_BASETEMP is not None
        self._basetemp = _SANDBOX_BASETEMP
    return self._basetemp


# The sandbox allows tmp_path creation but intermittently denies directory scans during
# pytest's dead-symlink cleanup pass. Disabling that cleanup keeps the standard tmp_path
# fixture usable without changing parser behavior or test semantics.
_pytest.pathlib.cleanup_dead_symlinks = lambda root: None
_pytest.tmpdir.cleanup_dead_symlinks = lambda root: None
_pytest.tmpdir.TempPathFactory.getbasetemp = _sandbox_safe_getbasetemp
