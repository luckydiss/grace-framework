# Adapter Probe Layer

GRACE `v1.3` adds deterministic adapter diagnostics for unfamiliar repositories.

## Purpose

Before bootstrap or framework extension work begins, an agent should be able to answer:

- which adapter would handle this file
- which language pack matched
- which construct-pack-extended surface is active
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

If the selected language pack already includes construct packs, `probe` still reports the same adapter class. The extension stays declarative inside pack metadata rather than introducing a new adapter family.

## `gaps`

`gaps` scans a repository scope and returns only files that still need framework work:

- `preview_only`
- `unsupported`
- `fallback`
- `ignored`

This gives the agent a deterministic backlog for language-pack, construct-pack, or file-policy expansion.

Once a construct pack closes a missing shape, the file should disappear from `gaps` without any parser-core changes.

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
