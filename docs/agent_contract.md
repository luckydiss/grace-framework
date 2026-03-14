# Agent Contract

GRACE is aimed at shell-driven coding agents that need a stable, machine-readable semantic editing protocol.

The intended consumer is a non-interactive agent that can run commands, read JSON, and then decide whether to navigate, patch, validate, or stop.

## Core Rule

Agents should treat the CLI as the stable integration surface.

- Source of truth remains inline GRACE annotations in code.
- The CLI does not create new identities.
- Semantic patch targets are always `anchor_id`, never line numbers.
- Parser entrypoints may dispatch through a language adapter, but CLI contracts and `GraceFileModel` semantics stay unchanged.

Current adapter baseline:

- Python reference adapter
- TypeScript pilot adapter
- Go pilot adapter
- cross-language parity fixtures
- adapter conformance coverage
- adapter evaluation coverage

## Scope

For `parse`, `validate`, `lint`, and `map`, `<path>` may be either:

- a single file supported by an installed adapter
- a directory containing GRACE-annotated files supported by installed adapters

Result payloads declare their scope explicitly:

- `"scope": "file"`
- `"scope": "project"`

## Directory Discovery Policy

When a directory path is provided, GRACE:

- recursively scans for files supported by installed adapters
- ignores common non-source directories such as `.git`, `__pycache__`, `.venv`, `venv`, `node_modules`, build caches, and `*.egg-info`
- considers a file a GRACE candidate only if its top-level comment preamble contains `@grace.module`
- sorts discovered files deterministically by relative path

This prevents test fixtures or embedded strings containing `@grace.*` from being treated as real GRACE modules.

If `[tool.grace]` exists in `pyproject.toml`, repo-root discovery also applies its `include` and `exclude` globs before candidate parsing. Explicit file and subdirectory targets override those repository-level filters so agents can still inspect excluded fixtures deliberately.

If no GRACE-annotated supported files are found, the command fails with:

- `"stage": "discovery"`
- non-zero exit code

## Recommended Agent Loop

1. `grace parse <path> --json`
2. `grace validate <path> --json`
3. `grace lint <path> --json`
4. `grace map <path> --json`
5. `grace query anchors <path> --json`
6. `grace read <path> <anchor_id> --json`
7. `grace query path <path> <source_anchor_id> <target_anchor_id> --json`
8. `grace impact <path> <anchor_id> --json`
9. `grace plan impact <path> <anchor_id> --json`
10. `grace adapter probe <file> --json`
11. `grace adapter gaps <path> --json`
12. `grace adapter eval <path> --json`
13. `grace bootstrap <path> --preview --json`
14. `grace bootstrap <path> --apply --json`
15. `grace patch <path> <anchor_id> <replacement_file> --dry-run --json`
16. `grace patch <path> <anchor_id> <replacement_file> --json`
17. `grace apply-plan <plan_file> --dry-run --json`
15. `grace apply-plan <plan_file> --json`
16. `grace validate <path> --json`
17. `grace lint <path> --json`
18. `grace clean <path> --dry-run --json`

For self-hosted GRACE development, the preferred scope is the annotated `grace/` package:

1. `grace map grace --json`
2. `grace query anchors grace --json`
3. `grace read grace <anchor_id> --json`
4. `grace query path grace <source_anchor_id> <target_anchor_id> --json`
5. `grace impact grace <anchor_id> --json`
6. `grace plan impact grace <anchor_id> --json`
7. `grace apply-plan <plan_file> --dry-run --preview --json`
8. `grace apply-plan <plan_file> --json`
9. `grace validate grace --json`
10. `grace lint grace --json`
11. `grace clean grace --dry-run --json`

This self-hosting loop is described in more detail in `docs/self_hosting.md`.
The workflow guidance and eval framing for agents are documented in `docs/agent_playbook.md`.

For unannotated or partially annotated repositories, prepend:

1. `grace bootstrap <path> --apply --json`
2. `grace lint <path> --json`

The expected contract is that `bootstrap` only creates deterministic placeholders. Real semantic text still belongs to later read/plan/patch work.

Before bootstrap or framework extension work begins, agents may prepend:

1. `grace adapter probe <file> --json`
2. `grace adapter gaps <path> --json`
3. `grace adapter eval <path> --json`

These commands are read-only. They classify language-pack coverage and file-policy verdicts, but they do not change parser, bootstrap, or patch semantics.

Repository-root policy:

- `parse . --json`, `map . --json`, `validate . --json`, and `lint . --json` are expected to succeed for the configured repository-root scope resolved through `[tool.grace]`
- parity fixtures may still intentionally reuse semantic identities, but they can be excluded from the default repo scope while remaining available through explicit subdirectory targets
- use curated subdirectories when you intentionally want to inspect excluded parity fixtures directly

## Multi-Language Behavior Guarantees

GRACE currently supports:

- Python as the reference adapter
- TypeScript as a pilot adapter
- Go as a pilot adapter

Across these adapters, the CLI contract remains stable because all runtime parsing normalizes into `GraceFileModel` before core layers run.

## Output Contract

For `parse`, `validate`, `lint`, `patch`, `impact`, `read`, and `plan`:

- `--json` prints a single JSON object to stdout.
- On `--json`, human-oriented multiline diagnostics are not emitted.
- Exit codes remain authoritative for success vs hard failure.

For `map`:

- `--json` prints the raw derived GRACE map payload.
- For directory input, this is a project semantic graph built from all discovered GRACE files.

## Exit Codes

- `parse`: `0` on success, non-zero on parse failure
- `validate`: `0` on parse + validation success, non-zero on parse or validation failure
- `lint`: `0` on clean result and on warnings, non-zero only on parse or validation failure
- `map`: `0` on success, non-zero on parse failure
- `patch`: `0` on success, non-zero on patch failure
- `apply-plan`: `0` on success, non-zero on plan-load failure or first patch failure
- `bootstrap`: `0` on preview or apply success, non-zero on discovery, parse, write, or validation failure
- `clean`: `0` on success, non-zero only when cleanup leaves failed artifact paths

## Command JSON Shapes

### `parse --json`

Success:

```json
{
  "ok": true,
  "command": "parse",
  "path": "examples/basic/pricing.py",
  "module_id": "billing.pricing",
  "block_count": 2,
  "file": {}
}
```

Project success:

```json
{
  "ok": true,
  "command": "parse",
  "scope": "project",
  "path": "repo/",
  "file_count": 2,
  "module_count": 2,
  "block_count": 3,
  "files": []
}
```

Failure:

```json
{
  "ok": false,
  "command": "parse",
  "stage": "parse",
  "path": "examples/basic/pricing.py",
  "errors": []
}
```

Project failure:

```json
{
  "ok": false,
  "command": "parse",
  "scope": "project",
  "stage": "parse",
  "path": "repo/",
  "parsed_file_count": 1,
  "failed_file_count": 1,
  "files": [],
  "errors": []
}
```

### `validate --json`

Success:

```json
{
  "ok": true,
  "command": "validate",
  "path": "examples/basic/pricing.py",
  "module_id": "billing.pricing",
  "block_count": 2,
  "validation": {
    "ok": true,
    "scope": "file"
  }
}
```

Project success:

```json
{
  "ok": true,
  "command": "validate",
  "scope": "project",
  "path": "repo/",
  "file_count": 2,
  "module_count": 2,
  "block_count": 3,
  "validation": {
    "ok": true,
    "scope": "project"
  }
}
```

Failure:

```json
{
  "ok": false,
  "command": "validate",
  "stage": "validate",
  "path": "examples/basic/pricing.py",
  "issues": []
}
```

### `lint --json`

Clean:

```json
{
  "ok": true,
  "command": "lint",
  "path": "examples/basic/pricing.py",
  "module_id": "billing.pricing",
  "warning_count": 0,
  "warnings": [],
  "clean": true
}
```

Project warnings:

```json
{
  "ok": true,
  "command": "lint",
  "scope": "project",
  "path": "repo/",
  "file_count": 2,
  "module_count": 2,
  "warning_count": 1,
  "warnings": [],
  "clean": false
}
```

Warnings:

```json
{
  "ok": true,
  "command": "lint",
  "path": "examples/basic/pricing.py",
  "module_id": "billing.pricing",
  "warning_count": 1,
  "warnings": [],
  "clean": false
}
```

Hard failure:

```json
{
  "ok": false,
  "command": "lint",
  "stage": "parse",
  "path": "examples/basic/pricing.py",
  "errors": []
}
```

or

```json
{
  "ok": false,
  "command": "lint",
  "stage": "validate",
  "path": "examples/basic/pricing.py",
  "issues": []
}
```

### `patch --json`

Success:

```json
{
  "ok": true,
  "command": "patch",
  "scope": "file",
  "target": {
    "path": "examples/basic/pricing.py",
    "anchor_id": "billing.pricing.apply_discount"
  },
  "path": "examples/basic/pricing.py",
  "anchor_id": "billing.pricing.apply_discount",
  "dry_run": false,
  "identity_preserved": true,
  "parse": {
    "status": "passed",
    "ok": true,
    "issue_count": 0
  },
  "validate": {
    "status": "passed",
    "ok": true,
    "issue_count": 0
  },
  "lint_warnings": [],
  "warning_count": 0,
  "rollback_performed": false,
  "before_hash": "sha256-before",
  "after_hash": "sha256-after",
  "preview": "--- before\n+++ after",
  "file": {}
}
```

Failure:

```json
{
  "ok": false,
  "command": "patch",
  "scope": "file",
  "target": {
    "path": "examples/basic/pricing.py",
    "anchor_id": "billing.pricing.apply_discount"
  },
  "stage": "identity",
  "path": "examples/basic/pricing.py",
  "anchor_id": "billing.pricing.apply_discount",
  "dry_run": true,
  "identity_preserved": false,
  "parse": {
    "status": "not_run",
    "ok": false,
    "issue_count": 0
  },
  "validate": {
    "status": "not_run",
    "ok": false,
    "issue_count": 0
  },
  "lint_warnings": [],
  "warning_count": 0,
  "rollback_performed": false,
  "before_hash": "sha256-before",
  "after_hash": "sha256-after",
  "preview": "--- before\n+++ after",
  "message": "replacement_source anchor_id ... does not match target anchor_id ...",
  "parse_errors": [],
  "validation_issues": []
}
```

Dry-run and preview semantics:

- `--dry-run` performs identity, parse, validate, and lint checks without writing to disk.
- `--preview` shows a semantic block diff and also avoids writing to disk.
- Lint warnings do not turn a successful patch into a hard failure.
- Parse or validation failure remains blocking.

### `apply-plan --json`

Success:

```json
{
  "ok": true,
  "command": "apply-plan",
  "scope": "project",
  "plan_path": "examples/basic/apply_discount.plan.json",
  "dry_run": false,
  "preview": false,
  "entry_count": 1,
  "applied_count": 1,
  "entries": [
    {
      "index": 0,
      "path": "examples/basic/pricing.py",
      "anchor_id": "billing.pricing.apply_discount",
      "operation": "replace_block",
      "result": {
        "ok": true
      }
    }
  ]
}
```

Failure:

```json
{
  "ok": false,
  "command": "apply-plan",
  "scope": "project",
  "stage": "entry_failure",
  "plan_path": "plan.json",
  "dry_run": false,
  "preview": false,
  "entry_count": 2,
  "applied_count": 1,
  "failed_index": 1,
  "failed_path": "repo/src/tax.py",
  "failed_anchor_id": "billing.tax.missing_anchor",
  "message": "patch plan failed at entry 1",
  "entries": []
}
```

Patch plan semantics:

- `PatchPlan` is a derived artifact, never source of truth.
- Current operation set contains only `replace_block`.
- `--dry-run` preflights the full plan without writing to disk.
- `--preview` produces entry-level semantic diffs without writing to disk.
- Entries are evaluated sequentially in plan order against a temporary project mirror.
- Execution stops on the first failing entry.
- Current baseline is transactional for `replace_block` plans:
  no earlier entry is flushed to disk if a later entry fails during preflight.

Failure taxonomy for current execution baseline:

- `patch` stages:
  `target_lookup`, `identity`, `parse`, `validate`
- `apply-plan` stages:
  `plan_load`, `entry_failure`
- `apply-plan entry_failure` always includes the nested patch result for the failing entry

### `clean --json`

Success:

```json
{
  "ok": true,
  "command": "clean",
  "path": "repo/",
  "scope_root": "/abs/repo",
  "dry_run": true,
  "cleaned_count": 2,
  "failed_count": 0,
  "cleaned_paths": [],
  "failed_paths": []
}
```

### `bootstrap --json`

Preview success:

```json
{
  "ok": true,
  "command": "bootstrap",
  "apply": false,
  "path": "legacy_repo/",
  "validated_file_count": 0,
  "files": [
    {
      "path": "legacy_repo/pricing.py",
      "module_id": "legacy_repo.pricing",
      "header_added": true,
      "generated_anchor_ids": [
        "legacy_repo.pricing.run"
      ]
    }
  ]
}
```

Apply failure:

```json
{
  "ok": false,
  "command": "bootstrap",
  "stage": "validate",
  "path": "legacy_repo/",
  "message": "Bootstrap validation failed",
  "validation_messages": [],
  "parse_failures": [],
  "rollback_performed": true
}
```

Failure:

```json
{
  "ok": false,
  "command": "clean",
  "path": "repo/",
  "scope_root": "/abs/repo",
  "dry_run": false,
  "cleaned_count": 1,
  "failed_count": 1,
  "cleaned_paths": [],
  "failed_paths": []
}
```

### `map --json`

For project input, `map --json` is the canonical cross-file semantic graph contract.

It contains:

- `modules[]`
- `anchors[]`
- `edges[]`

At minimum, `edges[]` includes:

- `module_has_anchor`
- `anchor_links_to_anchor`

Cross-file `grace.links` are preserved as `anchor_links_to_anchor` edges when the target anchor exists somewhere in the parsed project.

### `impact --json`

Success:

```json
{
  "ok": true,
  "command": "impact",
  "scope": "project",
  "path": "repo/",
  "target": "billing.tax.apply_tax",
  "data": {
    "direct_dependents": [],
    "transitive_dependents": [],
    "affected_modules": []
  }
}
```

Failure:

```json
{
  "ok": false,
  "command": "impact",
  "scope": "project",
  "stage": "impact",
  "path": "repo/",
  "target": "billing.unknown.anchor",
  "message": "anchor_id ... does not exist in impact scope"
}
```

### `query path --json`

Success with a path:

```json
{
  "ok": true,
  "command": "query",
  "query": "path",
  "scope": "project",
  "query_scope": "anchor",
  "path": "repo/",
  "source_anchor_id": "billing.pricing.choose_discount_strategy",
  "target_anchor_id": "billing.audit.record_tax",
  "found": true,
  "count": 3,
  "route": [],
  "edge_types": []
}
```

Success without a path:

```json
{
  "ok": true,
  "command": "query",
  "query": "path",
  "scope": "project",
  "query_scope": "anchor",
  "path": "repo/",
  "source_anchor_id": "billing.audit.record_tax",
  "target_anchor_id": "billing.pricing.choose_discount_strategy",
  "found": false,
  "count": 0,
  "route": [],
  "edge_types": []
}
```

Failure:

```json
{
  "ok": false,
  "command": "query",
  "query": "path",
  "scope": "project",
  "query_scope": "anchor",
  "stage": "query",
  "path": "repo/",
  "anchor_id": "billing.unknown.anchor",
  "message": "anchor_id ... does not exist in query scope"
}
```

### `read --json`

Success:

```json
{
  "ok": true,
  "command": "read",
  "scope": "project",
  "path": "repo/",
  "target": "billing.tax.apply_tax",
  "data": {
    "anchor_id": "billing.tax.apply_tax",
    "module_id": "billing.tax",
    "file_path": "repo/src/tax.py",
    "line_start": 6,
    "line_end": 9,
    "annotations": [],
    "code": "def apply_tax(amount: int) -> int:\n    return amount\n",
    "links": [],
    "neighbors": []
  }
}
```

### `plan impact --json`

Success:

```json
{
  "ok": true,
  "command": "plan",
  "mode": "impact",
  "scope": "project",
  "path": "repo/",
  "target": "billing.tax.apply_tax",
  "data": {
    "suggested_operations": [
      {
        "operation": "replace_block",
        "anchor_id": "billing.pricing.choose_discount_strategy"
      }
    ]
  }
}
```

Failure:

```json
{
  "ok": false,
  "command": "plan",
  "mode": "impact",
  "scope": "project",
  "stage": "plan",
  "path": "repo/",
  "target": "billing.unknown.anchor",
  "message": "anchor_id ... does not exist in planning scope"
}
```

Failure:

```json
{
  "ok": false,
  "command": "read",
  "scope": "project",
  "stage": "read",
  "path": "repo/",
  "target": "billing.unknown.anchor",
  "message": "anchor_id ... does not exist in read scope"
}
```

## Notes For Agents

- Prefer `--json` for machine workflows.
- For directory inputs, agents should treat discovered-file ordering as stable.
- Treat `lint` warnings as advisory, not blocking.
- Use `bootstrap --apply --json` only for structural initialization of unannotated code; do not treat TODO placeholders as completed semantics.
- Treat `patch --dry-run` as preflight, not as an applied change.
- Treat `apply-plan --dry-run` as plan-level preflight, not as an applied change.
- Use `read --json` to load one semantic block before patching instead of reading a whole file.
- Use `query path --json` to inspect the deterministic shortest semantic route between two anchors before planning a refactor across module boundaries.
- Use `impact --json` to inspect reverse dependents before touching a widely-linked anchor.
- Use `plan impact --json` to turn direct dependents into a deterministic patch proposal before writing a real plan file.
- Prefer `apply-plan` when the intended change spans multiple anchors.
- Use `clean --dry-run --json` to inspect leftover GRACE temp artifacts before they pollute later discovery or graph export.
- Treat `patch` success as provisional until a follow-up `validate --json` succeeds.
- Do not infer semantic identity from line numbers or file offsets.
- Treat repo `map --json` as the canonical cross-file graph view for current GRACE baseline.
