# Construct Packs

GRACE `v1.4` adds declarative construct packs on top of language packs.

## Purpose

Language packs answer:

- which suffixes route to a language
- which adapter family executes the language
- which base Tree-sitter spec should parse the file

Construct packs answer:

- which extra constructs should be recognized for an existing language
- which additional suffixes belong to those constructs
- whether a specialized grammar variant should replace the base grammar

This keeps extension work scoped to missing shapes instead of forcing a full new adapter.

## Current model

A construct pack may extend:

- file extensions
- line comment prefixes
- block comment delimiters
- Tree-sitter block queries
- language factory override

Construct packs do not change:

- `GraceFileModel`
- parser semantics
- patch semantics
- validator or linter contracts

## Built-in construct packs

Current built-in pack:

- `typescript.tsx_function_components`

It extends the TypeScript pilot with:

- `.tsx` routing
- TSX grammar selection
- exported function component support
- exported arrow component support
- exported class/object wrapper coverage where the underlying semantic block is still deterministic

## Agent workflow

When a repository exposes code-like files that are still `preview_only`:

1. `grace adapter probe <file>`
2. `grace adapter gaps <path>`
3. add a construct pack if the base language is already known
4. rerun `grace adapter eval <path>`
5. continue with `grace bootstrap`

Construct packs are the preferred extension mechanism when the language already exists and only specific frontend or framework shapes are missing.
