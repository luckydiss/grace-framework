# @grace.module grace.tree_sitter_adapter
# @grace.purpose Provide minimal Tree-sitter substrate helpers for non-Python pilot adapters without changing GRACE core semantics.
# @grace.interfaces TreeSitterSourceFile; load_tree_sitter_source(file_path, language_factory)->TreeSitterSourceFile; iter_tree_nodes(root_node)->Iterator[Node]; strip_comment_delimiters(comment_text)->tuple[str, ...]
# @grace.invariant Tree-sitter helpers remain substrate-only; adapters still own GRACE annotation binding and GraceFileModel emission.
# @grace.invariant Tree-sitter parsing must not redefine GRACE source-of-truth semantics or normalized core output models.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from tree_sitter import Language, Node, Parser, Tree


# @grace.anchor grace.tree_sitter_adapter.TreeSitterSourceFile
# @grace.complexity 2
@dataclass(frozen=True, slots=True)
class TreeSitterSourceFile:
    path: Path
    source_text: str
    source_bytes: bytes
    tree: Tree


# @grace.anchor grace.tree_sitter_adapter.load_tree_sitter_source
# @grace.complexity 3
def load_tree_sitter_source(
    file_path: str | Path,
    language_factory: Callable[[], object],
) -> TreeSitterSourceFile:
    source_path = Path(file_path)
    source_text = source_path.read_text(encoding="utf-8")
    source_bytes = source_text.encode("utf-8")
    parser = Parser(Language(language_factory()))
    tree = parser.parse(source_bytes)
    return TreeSitterSourceFile(
        path=source_path,
        source_text=source_text,
        source_bytes=source_bytes,
        tree=tree,
    )


# @grace.anchor grace.tree_sitter_adapter.iter_tree_nodes
# @grace.complexity 2
def iter_tree_nodes(root_node: Node) -> Iterator[Node]:
    stack = [root_node]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(node.children))


# @grace.anchor grace.tree_sitter_adapter.strip_comment_delimiters
# @grace.complexity 3
def strip_comment_delimiters(comment_text: str) -> tuple[str, ...]:
    stripped = comment_text.strip()
    if stripped.startswith("//"):
        return (stripped[2:].strip(),)
    if stripped.startswith("/*") and stripped.endswith("*/"):
        body = stripped[2:-2]
        normalized_lines: list[str] = []
        for line in body.splitlines():
            normalized_lines.append(line.lstrip(" *").rstrip())
        return tuple(line for line in normalized_lines if line)
    return (stripped,)
