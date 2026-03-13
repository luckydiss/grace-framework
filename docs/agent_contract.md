# Agent Contract

GRACE v0.6 development is aimed at shell-driven coding agents.

The intended consumer is a non-interactive agent that can run commands, read JSON, and then decide whether to navigate, patch, validate, or stop.

## Core Rule

Agents should treat the CLI as the stable integration surface.

- Source of truth remains inline GRACE annotations in code.
- The CLI does not create new identities.
- Semantic patch targets are always `anchor_id`, never line numbers.
- Parser entrypoints may dispatch through a language adapter, but CLI contracts and `GraceFileModel` semantics stay unchanged.

## Scope

For `parse`, `validate`, `lint`, and `map`, `<path>` may be either:

- a single Python file
- a directory containing GRACE-annotated Python files

Result payloads declare their scope explicitly:

- `"scope": "file"`
- `"scope": "project"`

## Directory Discovery Policy

When a directory path is provided, GRACE:

- recursively scans for `.py` files
- ignores common non-source directories such as `.git`, `__pycache__`, `.venv`, `venv`, `node_modules`, build caches, and `*.egg-info`
- considers a file a GRACE candidate only if its source contains `@grace.`
- sorts discovered files deterministically by relative path

If no GRACE-annotated Python files are found, the command fails with:

- `"stage": "discovery"`
- non-zero exit code

## Recommended Agent Loop

1. `grace parse <path> --json`
2. `grace validate <path> --json`
3. `grace lint <path> --json`
4. `grace map <path> --json`
5. `grace query anchors <path> --json`
6. `grace read <path> <anchor_id> --json`
7. `grace impact <path> <anchor_id> --json`
8. `grace plan impact <path> <anchor_id> --json`
9. `grace patch <path> <anchor_id> <replacement_file> --dry-run --json`
10. `grace patch <path> <anchor_id> <replacement_file> --json`
11. `grace apply-plan <plan_file> --dry-run --json`
12. `grace apply-plan <plan_file> --json`
13. `grace validate <path> --json`
14. `grace lint <path> --json`

For self-hosted GRACE development, the preferred scope is the annotated `grace/` package:

1. `grace map grace --json`
2. `grace query anchors grace --json`
3. `grace read grace <anchor_id> --json`
4. `grace impact grace <anchor_id> --json`
5. `grace plan impact grace <anchor_id> --json`
6. `grace apply-plan <plan_file> --dry-run --preview --json`
7. `grace apply-plan <plan_file> --json`
8. `grace validate grace --json`
9. `grace lint grace --json`

This self-hosting loop is described in more detail in `docs/self_hosting.md`.
The workflow guidance and eval framing for agents are documented in `docs/agent_playbook.md`.

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
- Entries are applied sequentially in plan order.
- Execution stops on the first failing entry.
- Current baseline is not transactional:
  already-applied earlier entries are not rolled back automatically.

Failure taxonomy for current execution baseline:

- `patch` stages:
  `target_lookup`, `identity`, `parse`, `validate`
- `apply-plan` stages:
  `plan_load`, `entry_failure`
- `apply-plan entry_failure` always includes the nested patch result for the failing entry

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
- Treat `patch --dry-run` as preflight, not as an applied change.
- Treat `apply-plan --dry-run` as plan-level preflight, not as an applied change.
- Use `read --json` to load one semantic block before patching instead of reading a whole file.
- Use `impact --json` to inspect reverse dependents before touching a widely-linked anchor.
- Use `plan impact --json` to turn direct dependents into a deterministic patch proposal before writing a real plan file.
- Prefer `apply-plan` when the intended change spans multiple anchors.
- Treat `patch` success as provisional until a follow-up `validate --json` succeeds.
- Do not infer semantic identity from line numbers or file offsets.
- Treat repo `map --json` as the canonical cross-file graph view for current GRACE baseline.
