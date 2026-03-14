"""External language and construct spec loading for GRACE."""

from __future__ import annotations

import ctypes
import importlib
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from tree_sitter import Language

from grace.construct_pack import GraceConstructPack, apply_construct_packs
from grace.grammar_manager import load_installed_grammar_record
from grace.language_pack import GraceLanguagePack, GraceLanguagePackStatus, build_treesitter_pack
from grace.models import BlockKind
from grace.repo_config import load_repo_config
from grace.treesitter_base import TreeSitterBlockQuerySpec, TreeSitterLanguageSpec


_PYCAPSULE_NEW = ctypes.pythonapi.PyCapsule_New
_PYCAPSULE_NEW.restype = ctypes.py_object
_PYCAPSULE_NEW.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p]


class QuerySpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str
    kind: str
    symbol_capture: str
    block_capture: str = "block"
    owner_capture: str | None = None
    async_capture: str | None = None
    line_start_capture: str | None = None
    qualified_name_template: str | None = None
    promote_async_kind: str | None = None


class GrammarSpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["python_callable", "compiled_library", "installed"]
    target: str | None = None
    library_path: str | None = None
    symbol: str | None = None

    @model_validator(mode="after")
    def _validate_provider_fields(self) -> "GrammarSpecModel":
        if self.provider == "python_callable" and not self.target:
            raise ValueError("python_callable grammars require target")
        if self.provider == "compiled_library" and (not self.library_path or not self.symbol):
            raise ValueError("compiled_library grammars require library_path and symbol")
        if self.provider == "installed" and not self.symbol:
            return self
        return self


class LanguagePackSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    language_name: str
    file_extensions: tuple[str, ...]
    status: Literal["reference", "pilot", "experimental"]
    bootstrap_safe: bool = True
    adapter_factory: str | None = None
    line_comment_prefixes: tuple[str, ...] = ()
    block_comment_delimiters: tuple[tuple[str, str], ...] = ()
    construct_pack_names: tuple[str, ...] = ()
    grammar: GrammarSpecModel
    queries: tuple[QuerySpecModel, ...]

    @field_validator(
        "file_extensions",
        "line_comment_prefixes",
        "construct_pack_names",
        mode="before",
    )
    @classmethod
    def _coerce_flat_tuples(cls, value: object) -> object:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("block_comment_delimiters", mode="before")
    @classmethod
    def _coerce_delimiters(cls, value: object) -> object:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(tuple(item) for item in value)
        return value


class ConstructPackSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pack_name: str
    language_name: str
    additional_file_extensions: tuple[str, ...] = ()
    additional_line_comment_prefixes: tuple[str, ...] = ()
    additional_block_comment_delimiters: tuple[tuple[str, str], ...] = ()
    bootstrap_safe: bool | None = None
    override_grammar: GrammarSpecModel | None = None
    queries: tuple[QuerySpecModel, ...] = Field(default_factory=tuple)

    @field_validator(
        "additional_file_extensions",
        "additional_line_comment_prefixes",
        mode="before",
    )
    @classmethod
    def _coerce_flat_tuples(cls, value: object) -> object:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("additional_block_comment_delimiters", mode="before")
    @classmethod
    def _coerce_delimiters(cls, value: object) -> object:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(tuple(item) for item in value)
        return value


def _status(value: str) -> GraceLanguagePackStatus:
    return GraceLanguagePackStatus(value)


def _block_kind(value: str | None) -> BlockKind | None:
    if value is None:
        return None
    return BlockKind(value)


def _project_root(path: str | Path) -> Path:
    candidate = Path(path).expanduser().resolve()
    config = load_repo_config(candidate)
    if config is not None:
        return config.root
    return candidate if candidate.is_dir() else candidate.parent


def _builtin_root() -> Path:
    return Path(__file__).resolve().parent / "specs"


def _resolve_import_target(target: str):
    module_name, _, attribute = target.partition(":")
    if not module_name or not attribute:
        raise ValueError(f"invalid import target {target!r}")
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


def _shared_library_language_factory(library_path: Path, symbol: str):
    cache: dict[str, object] = {}

    def language_factory():
        if "capsule" in cache:
            return cache["capsule"]
        library = ctypes.CDLL(str(library_path))
        function = getattr(library, symbol)
        function.restype = ctypes.c_void_p
        pointer = function()
        if not pointer:
            raise RuntimeError(f"grammar symbol {symbol!r} in {library_path} returned NULL")
        capsule = _PYCAPSULE_NEW(pointer, b"tree_sitter.Language", None)
        cache["library"] = library
        cache["capsule"] = capsule
        return capsule

    return language_factory


def _resolve_grammar_callable(grammar: GrammarSpecModel, *, root: Path):
    if grammar.provider == "python_callable":
        return _resolve_import_target(grammar.target or "")
    if grammar.provider == "compiled_library":
        library_path = Path(grammar.library_path or "")
        if not library_path.is_absolute():
            library_path = (root / library_path).resolve()
        return _shared_library_language_factory(library_path, grammar.symbol or "")
    record = load_installed_grammar_record(grammar.target or grammar.symbol or "", root)
    if record is None:
        raise LookupError(f"no installed grammar record for {(grammar.target or grammar.symbol or '')!r}")
    if record.provider == "python_callable":
        return _resolve_import_target(record.target or "")
    library_path = Path(record.library_path or "")
    if not library_path.is_absolute():
        library_path = (_project_root(root) / ".grace" / "grammars" / library_path).resolve()
    return _shared_library_language_factory(library_path, record.symbol or "")


def _load_toml_model(path: Path, model_type):
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    return model_type.model_validate(payload)


def _query_specs(queries: tuple[QuerySpecModel, ...]) -> tuple[TreeSitterBlockQuerySpec, ...]:
    return tuple(
        TreeSitterBlockQuerySpec(
            query=query.query,
            kind=BlockKind(query.kind),
            symbol_capture=query.symbol_capture,
            block_capture=query.block_capture,
            owner_capture=query.owner_capture,
            async_capture=query.async_capture,
            line_start_capture=query.line_start_capture,
            qualified_name_template=query.qualified_name_template,
            promote_async_kind=_block_kind(query.promote_async_kind),
        )
        for query in queries
    )


def _language_spec_factory(spec: LanguagePackSpec, *, root: Path):
    def spec_factory() -> TreeSitterLanguageSpec:
        return TreeSitterLanguageSpec(
            language_name=spec.language_name,
            file_extensions=spec.file_extensions,
            language_factory=_resolve_grammar_callable(spec.grammar, root=root),
            line_comment_prefixes=spec.line_comment_prefixes,
            block_comment_delimiters=spec.block_comment_delimiters,
            block_query_specs=_query_specs(spec.queries),
        )

    return spec_factory


def _override_language_factory(grammar: GrammarSpecModel, *, root: Path):
    def language_factory() -> object:
        return _resolve_grammar_callable(grammar, root=root)()

    return language_factory


def _adapter_factory(target: str | None):
    if not target:
        return None

    def factory() -> object:
        adapter_type = _resolve_import_target(target)
        return adapter_type()

    return factory


def _default_construct_dir(language_name: str, *, builtin: bool, root: Path) -> Path:
    if builtin:
        return _builtin_root() / "constructs" / language_name
    return root / ".grace" / "specs" / "constructs" / language_name


def _repo_construct_dirs(path: str | Path, language_name: str) -> tuple[Path, ...]:
    root = _project_root(path)
    config = load_repo_config(root)
    configured = ()
    if config is not None:
        configured = tuple((root / relative / language_name).resolve() for relative in getattr(config, "construct_spec_dirs", ()))
    return (_default_construct_dir(language_name, builtin=False, root=root), *configured)


def _repo_language_dirs(path: str | Path) -> tuple[Path, ...]:
    root = _project_root(path)
    config = load_repo_config(root)
    configured = ()
    if config is not None:
        configured = tuple((root / relative).resolve() for relative in getattr(config, "language_spec_dirs", ()))
    return (root / ".grace" / "specs" / "languages", *configured)


def load_builtin_construct_packs(language_name: str | None = None) -> tuple[GraceConstructPack, ...]:
    root = _builtin_root() / "constructs"
    if not root.is_dir():
        return ()
    return _load_construct_packs_from_dirs(
        tuple(path for path in (root / language_name,) if language_name is not None and path.is_dir()) if language_name else tuple(path for path in root.iterdir() if path.is_dir()),
        spec_root=_builtin_root(),
    )


def load_construct_packs_for_path(path: str | Path, language_name: str) -> tuple[GraceConstructPack, ...]:
    builtin_dir = _default_construct_dir(language_name, builtin=True, root=_builtin_root())
    candidate_dirs = tuple(directory for directory in (builtin_dir, *_repo_construct_dirs(path, language_name)) if directory.is_dir())
    return _load_construct_packs_from_dirs(candidate_dirs, spec_root=_project_root(path))


def _load_construct_packs_from_dirs(directories: tuple[Path, ...], *, spec_root: Path) -> tuple[GraceConstructPack, ...]:
    packs_by_name: dict[str, GraceConstructPack] = {}
    for directory in directories:
        for path in sorted(directory.glob("*.toml")):
            spec = _load_toml_model(path, ConstructPackSpec)
            pack = GraceConstructPack(
                pack_name=spec.pack_name,
                language_name=spec.language_name,
                additional_file_extensions=spec.additional_file_extensions,
                additional_line_comment_prefixes=spec.additional_line_comment_prefixes,
                additional_block_comment_delimiters=spec.additional_block_comment_delimiters,
                additional_block_query_specs=_query_specs(spec.queries),
                override_language_factory=_override_language_factory(spec.override_grammar, root=spec_root) if spec.override_grammar is not None else None,
                bootstrap_safe=spec.bootstrap_safe,
            )
            packs_by_name[pack.pack_name] = pack
    return tuple(packs_by_name[name] for name in sorted(packs_by_name))


def load_builtin_language_pack(language_name: str) -> GraceLanguagePack:
    path = _builtin_root() / "languages" / f"{language_name}.toml"
    spec = _load_toml_model(path, LanguagePackSpec)
    construct_packs = load_builtin_construct_packs(language_name)
    return _build_pack_from_spec(spec, _builtin_root(), construct_packs)


@lru_cache(maxsize=1)
def load_registered_builtin_language_packs() -> tuple[GraceLanguagePack, ...]:
    language_dir = _builtin_root() / "languages"
    if not language_dir.is_dir():
        return ()
    return tuple(
        load_builtin_language_pack(path.stem)
        for path in sorted(language_dir.glob("*.toml"))
    )


def load_language_pack_for_path(path: str | Path) -> GraceLanguagePack | None:
    resolved_path = Path(path).expanduser().resolve()
    suffix = resolved_path.suffix.lower()
    builtin_by_extension = {
        extension: pack
        for pack in load_registered_builtin_language_packs()
        for extension in pack.file_extensions
    }
    candidate = builtin_by_extension.get(suffix)

    for directory in _repo_language_dirs(resolved_path):
        if not directory.is_dir():
            continue
        for spec_path in sorted(directory.glob("*.toml")):
            spec = _load_toml_model(spec_path, LanguagePackSpec)
            if suffix not in spec.file_extensions:
                continue
            construct_packs = load_construct_packs_for_path(resolved_path, spec.language_name)
            return _build_pack_from_spec(spec, _project_root(resolved_path), construct_packs)

    if candidate is None:
        return None

    if suffix not in candidate.file_extensions:
        return None

    language_name = candidate.language_name
    construct_packs = load_construct_packs_for_path(resolved_path, language_name)
    if construct_packs:
        builtin_spec = _load_toml_model(_builtin_root() / "languages" / f"{language_name}.toml", LanguagePackSpec)
        return _build_pack_from_spec(builtin_spec, _project_root(resolved_path), construct_packs)
    return candidate


def _build_pack_from_spec(
    spec: LanguagePackSpec,
    root: Path,
    construct_packs: tuple[GraceConstructPack, ...],
) -> GraceLanguagePack:
    base_factory = _language_spec_factory(spec, root=root)
    construct_pack_names = tuple(pack.pack_name for pack in construct_packs)

    def spec_factory() -> TreeSitterLanguageSpec:
        return apply_construct_packs(base_factory(), construct_packs)

    merged_spec = spec_factory()
    bootstrap_safe = spec.bootstrap_safe and all(pack.bootstrap_safe is not False for pack in construct_packs)
    return build_treesitter_pack(
        language_name=spec.language_name,
        file_extensions=merged_spec.file_extensions,
        status=_status(spec.status),
        spec_factory=spec_factory,
        adapter_factory=_adapter_factory(spec.adapter_factory),
        bootstrap_safe=bootstrap_safe,
        construct_pack_names=construct_pack_names,
    )


def load_repo_spec_paths(path: str | Path) -> tuple[Path, ...]:
    root = _project_root(path)
    return tuple(directory for directory in _repo_language_dirs(root) if directory.is_dir())


__all__ = [
    "ConstructPackSpec",
    "GrammarSpecModel",
    "LanguagePackSpec",
    "QuerySpecModel",
    "load_builtin_construct_packs",
    "load_builtin_language_pack",
    "load_construct_packs_for_path",
    "load_language_pack_for_path",
    "load_registered_builtin_language_packs",
    "load_repo_spec_paths",
]
