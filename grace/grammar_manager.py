# @grace.module grace.grammar_manager
# @grace.purpose Manage external Tree-sitter grammar records and cached compiled libraries so repo-local language specs can resolve grammars without editing GRACE package code.
# @grace.interfaces GrammarInstallRecord, resolve_grammar_cache_dir, list_installed_grammars, install_grammar_record, load_installed_grammar_record, build_grammar_from_source
# @grace.invariant Grammar management remains explicit and auditable; normal parse flows may read cached grammar records, but installation and compilation happen only through dedicated commands or explicit manifests.

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from grace.repo_config import load_repo_config


# @grace.anchor grace.grammar_manager.GrammarInstallRecord
# @grace.complexity 2
class GrammarInstallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    language_name: str
    provider: Literal["python_callable", "compiled_library"]
    target: str | None = None
    library_path: str | None = None
    symbol: str | None = None

    @model_validator(mode="after")
    def _validate_provider_fields(self) -> "GrammarInstallRecord":
        if self.provider == "python_callable" and not self.target:
            raise ValueError("python_callable grammar records require target")
        if self.provider == "compiled_library" and (not self.library_path or not self.symbol):
            raise ValueError("compiled_library grammar records require library_path and symbol")
        return self


def _repo_root(path: str | Path) -> Path:
    candidate = Path(path).expanduser().resolve()
    config = load_repo_config(candidate)
    if config is not None:
        return config.root
    return candidate if candidate.is_dir() else candidate.parent


# @grace.anchor grace.grammar_manager.resolve_grammar_cache_dir
# @grace.complexity 2
def resolve_grammar_cache_dir(path: str | Path) -> Path:
    root = _repo_root(path)
    config = load_repo_config(root)
    relative = config.grammar_cache_dir if config is not None else ".grace/grammars"
    return (root / relative).resolve()


def _record_path(language_name: str, path: str | Path) -> Path:
    return resolve_grammar_cache_dir(path) / f"{language_name}.toml"


# @grace.anchor grace.grammar_manager.load_installed_grammar_record
# @grace.complexity 2
def load_installed_grammar_record(language_name: str, path: str | Path) -> GrammarInstallRecord | None:
    record_path = _record_path(language_name, path)
    if not record_path.is_file():
        return None
    payload = tomllib.loads(record_path.read_text(encoding="utf-8"))
    return GrammarInstallRecord.model_validate(payload)


# @grace.anchor grace.grammar_manager.list_installed_grammars
# @grace.complexity 2
def list_installed_grammars(path: str | Path) -> tuple[GrammarInstallRecord, ...]:
    cache_dir = resolve_grammar_cache_dir(path)
    if not cache_dir.exists():
        return ()
    records: list[GrammarInstallRecord] = []
    for record_path in sorted(cache_dir.glob("*.toml")):
        payload = tomllib.loads(record_path.read_text(encoding="utf-8"))
        records.append(GrammarInstallRecord.model_validate(payload))
    return tuple(records)


# @grace.anchor grace.grammar_manager.install_grammar_record
# @grace.complexity 2
def install_grammar_record(record: GrammarInstallRecord, path: str | Path) -> Path:
    cache_dir = resolve_grammar_cache_dir(path)
    cache_dir.mkdir(parents=True, exist_ok=True)
    record_path = cache_dir / f"{record.language_name}.toml"
    payload = record.model_dump(mode="json")
    lines = []
    for key, value in payload.items():
        if value is None:
            continue
        lines.append(f'{key} = "{value}"')
    record_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return record_path


def _shared_library_suffix() -> str:
    if sys.platform.startswith("win"):
        return ".dll"
    if sys.platform == "darwin":
        return ".dylib"
    return ".so"


def _default_symbol(language_name: str) -> str:
    return f"tree_sitter_{language_name.replace('-', '_')}"


def _detect_compiler() -> list[str]:
    for candidate in ("clang", "gcc", "cc"):
        if shutil.which(candidate):
            return [candidate]
    if os.name == "nt" and shutil.which("cl"):
        return ["cl"]
    raise RuntimeError("no supported C compiler found for grammar build")


def _compile_shared_library(source_dir: Path, output_path: Path) -> None:
    parser_path = source_dir / "src" / "parser.c"
    if not parser_path.is_file():
        raise FileNotFoundError(f"missing parser.c under {source_dir / 'src'}")

    scanner_sources = [
        candidate
        for candidate in (
            source_dir / "src" / "scanner.c",
            source_dir / "src" / "scanner.cc",
            source_dir / "src" / "scanner.cpp",
        )
        if candidate.is_file()
    ]
    compiler = _detect_compiler()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if compiler[0] == "cl":
        command = [
            "cl",
            "/LD",
            "/O2",
            f"/I{source_dir / 'src'}",
            str(parser_path),
            *map(str, scanner_sources),
            f"/Fe:{output_path}",
        ]
    else:
        command = [
            *compiler,
            "-shared",
            "-fPIC",
            "-O2",
            f"-I{source_dir / 'src'}",
            str(parser_path),
            *map(str, scanner_sources),
            "-o",
            str(output_path),
        ]
    subprocess.run(command, check=True, cwd=source_dir)


# @grace.anchor grace.grammar_manager.build_grammar_from_source
# @grace.complexity 4
# @grace.belief Grammar builds should be explicit and cached so repo-local language specs can become runnable without editing package dependencies, while the normal parse path stays free of network or compiler side effects.
def build_grammar_from_source(
    language_name: str,
    source_dir: str | Path,
    path: str | Path,
    *,
    symbol: str | None = None,
) -> Path:
    resolved_source_dir = Path(source_dir).expanduser().resolve()
    cache_dir = resolve_grammar_cache_dir(path)
    output_path = cache_dir / f"{language_name}{_shared_library_suffix()}"
    _compile_shared_library(resolved_source_dir, output_path)
    install_grammar_record(
        GrammarInstallRecord(
            language_name=language_name,
            provider="compiled_library",
            library_path=output_path.name,
            symbol=symbol or _default_symbol(language_name),
        ),
        path,
    )
    return output_path


__all__ = [
    "GrammarInstallRecord",
    "build_grammar_from_source",
    "install_grammar_record",
    "list_installed_grammars",
    "load_installed_grammar_record",
    "resolve_grammar_cache_dir",
]
