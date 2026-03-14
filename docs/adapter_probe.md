# Adapter Probe Layer

GRACE `v1.3` adds deterministic adapter diagnostics for unfamiliar repositories.

## Purpose

Before bootstrap or framework extension work begins, an agent should be able to answer:

- which adapter would handle this file
- which language pack matched
- which file-policy verdict applies
- which files in a repository still represent coverage gaps

## Commands

```bash
grace adapter probe path/to/file.py
grace adapter gaps repo_root/
grace adapter eval repo_root/
```

## `probe`

`probe` returns a file-level diagnostic:

- selected language pack
- adapter family
- adapter class
- file class
- file-policy verdict
- bootstrap safety
- deterministic reason string

## `gaps`

`gaps` scans a repository scope and returns only files that still need framework work:

- `preview_only`
- `unsupported`
- `fallback`
- `ignored`

This gives the agent a deterministic backlog for language-pack, construct-pack, or file-policy expansion.

## `eval`

`eval` summarizes repository coverage:

- file counts
- file-class counts
- policy-verdict counts
- language counts
- gap counts

## Non-Goals

This layer does not:

- infer business meaning
- patch files
- change parser semantics
- invent support for unsupported syntax

It only reports current runtime coverage and current policy constraints.
