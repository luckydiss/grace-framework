# Agent Contract

GRACE v0.2 development is aimed at shell-driven coding agents.

The intended consumer is a non-interactive agent that can run commands, read JSON, and then decide whether to navigate, patch, validate, or stop.

## Core Rule

Agents should treat the CLI as the stable integration surface.

- Source of truth remains inline GRACE annotations in code.
- The CLI does not create new identities.
- Semantic patch targets are always `anchor_id`, never line numbers.

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
5. `grace patch <path> <anchor_id> <replacement_file> --json`
6. `grace validate <path> --json`
7. `grace lint <path> --json`

## Output Contract

For `parse`, `validate`, `lint`, and `patch`:

- `--json` prints a single JSON object to stdout.
- On `--json`, human-oriented multiline diagnostics are not emitted.
- Exit codes remain authoritative for success vs hard failure.

For `map`:

- `--json` prints the raw derived GRACE map payload.
- For directory input, this is a project map built from all discovered GRACE files.

## Exit Codes

- `parse`: `0` on success, non-zero on parse failure
- `validate`: `0` on parse + validation success, non-zero on parse or validation failure
- `lint`: `0` on clean result and on warnings, non-zero only on parse or validation failure
- `map`: `0` on success, non-zero on parse failure
- `patch`: `0` on success, non-zero on patch failure

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
  "path": "examples/basic/pricing.py",
  "anchor_id": "billing.pricing.apply_discount",
  "warning_count": 0,
  "lint_issues": [],
  "file": {}
}
```

Failure:

```json
{
  "ok": false,
  "command": "patch",
  "stage": "identity",
  "path": "examples/basic/pricing.py",
  "anchor_id": "billing.pricing.apply_discount",
  "message": "replacement_source anchor_id ... does not match target anchor_id ...",
  "parse_errors": [],
  "validation_issues": []
}
```

## Notes For Agents

- Prefer `--json` for machine workflows.
- For directory inputs, agents should treat discovered-file ordering as stable.
- Treat `lint` warnings as advisory, not blocking.
- Treat `patch` success as provisional until a follow-up `validate --json` succeeds.
- Do not infer semantic identity from line numbers or file offsets.
- Current baseline limitation:
  cross-file `grace.links` are not yet part of the parse-stable project contract because link resolution is still file-local in the parser.
