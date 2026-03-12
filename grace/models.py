from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BlockKind(str, Enum):
    FUNCTION = "function"
    ASYNC_FUNCTION = "async_function"
    CLASS = "class"
    METHOD = "method"


class ParseErrorCode(str, Enum):
    PYTHON_SYNTAX_ERROR = "python_syntax_error"
    UNKNOWN_GRACE_ANNOTATION = "unknown_grace_annotation"
    EMPTY_ANNOTATION_PAYLOAD = "empty_annotation_payload"
    DUPLICATE_MODULE_ANNOTATION = "duplicate_module_annotation"
    MODULE_ANNOTATION_OUT_OF_ORDER = "module_annotation_out_of_order"
    MODULE_ANNOTATION_AFTER_BLOCKS = "module_annotation_after_blocks"
    MISSING_REQUIRED_MODULE_ANNOTATION = "missing_required_module_annotation"
    INVALID_BLOCK_ANNOTATION_ORDER = "invalid_block_annotation_order"
    DUPLICATE_BLOCK_ANNOTATION = "duplicate_block_annotation"
    BLOCK_ANNOTATION_WITHOUT_ANCHOR = "block_annotation_without_anchor"
    INVALID_COMPLEXITY = "invalid_complexity"
    MISSING_REQUIRED_BELIEF = "missing_required_belief"
    ORPHAN_BLOCK_ANNOTATIONS = "orphan_block_annotations"
    INVALID_BINDING_TARGET = "invalid_binding_target"
    ARBITRARY_CODE_BETWEEN_ANNOTATIONS_AND_BLOCK = "arbitrary_code_between_annotations_and_block"
    DUPLICATE_ANCHOR_ID = "duplicate_anchor_id"
    UNKNOWN_LINK_TARGET = "unknown_link_target"


class GraceParseIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ParseErrorCode
    message: str = Field(min_length=1)
    line: int | None = Field(default=None, ge=1)


class GraceModuleMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    module_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    interfaces: str = Field(min_length=1)
    invariants: tuple[str, ...] = Field(min_length=1)

    @field_validator("module_id", "purpose", "interfaces", mode="before")
    @classmethod
    def _strip_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("invariants", mode="before")
    @classmethod
    def _coerce_invariants(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(item.strip() if isinstance(item, str) else item for item in value)
        return value

    @field_validator("invariants")
    @classmethod
    def _validate_invariants(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item for item in value):
            raise ValueError("module invariants must be non-empty")
        return value


class GraceBlockMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_id: str = Field(min_length=1)
    kind: BlockKind
    symbol_name: str = Field(min_length=1)
    qualified_name: str = Field(min_length=1)
    is_async: bool = False
    complexity: int = Field(ge=1, le=10)
    belief: str | None = None
    links: tuple[str, ...] = Field(default_factory=tuple)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)

    @field_validator("anchor_id", "symbol_name", "qualified_name", mode="before")
    @classmethod
    def _strip_identifier_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("belief", mode="before")
    @classmethod
    def _strip_optional_belief(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("links", mode="before")
    @classmethod
    def _coerce_links(cls, value: object) -> object:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(item.strip() if isinstance(item, str) else item for item in value)
        return value

    @field_validator("links")
    @classmethod
    def _validate_links(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item for item in value):
            raise ValueError("links must contain non-empty anchor ids")
        return value

    @model_validator(mode="after")
    def _validate_belief_threshold(self) -> "GraceBlockMetadata":
        if self.complexity >= 6 and not self.belief:
            raise ValueError("grace.belief is required when grace.complexity >= 6")
        return self


class GraceFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    module: GraceModuleMetadata
    blocks: tuple[GraceBlockMetadata, ...]


class GraceParseSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[True] = True
    file: GraceFileModel


class GraceParseFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[False] = False
    path: Path
    errors: tuple[GraceParseIssue, ...] = Field(min_length=1)


GraceParseResult = GraceParseSuccess | GraceParseFailure


__all__ = [
    "BlockKind",
    "GraceBlockMetadata",
    "GraceFileModel",
    "GraceModuleMetadata",
    "GraceParseFailure",
    "GraceParseIssue",
    "GraceParseResult",
    "GraceParseSuccess",
    "ParseErrorCode",
]
