# GRACE Self-Hosting

GRACE self-hosting means developing the GRACE repository through GRACE-native operations rather than treating the framework as a tool that only works on examples.

The current self-hosting baseline covers these annotated core modules:

- `grace/parser.py`
- `grace/patcher.py`
- `grace/cli.py`
- `grace/plan.py`
- `grace/validator.py`
- `grace/map.py`
- `grace/linter.py`

This scope is sufficient to dogfood the core execution loop:

- `parse`
- `validate`
- `lint`
- `map`
- `patch`
- `apply-plan`

## Invariants

- Inline GRACE annotations remain the only source of truth.
- Self-hosting does not permit sidecar-first editing.
- Patch operations stay anchor-driven and identity-preserving.
- Parse or validation failure after a write remains rollback-blocking.
- Lint warnings are acceptable dogfood output and should be interpreted as guidance, not silent success.

## Canonical Workflow

For development inside the annotated `grace/` scope:

1. Build the repo map:

```bash
grace map grace --json
```

2. Choose a target `anchor_id`.

3. Prepare a full replacement semantic block for that anchor.

4. Run a preflight patch:

```bash
grace patch <file> <anchor_id> <replacement_file> --dry-run --preview --json
```

5. If the preflight passes, apply the patch:

```bash
grace patch <file> <anchor_id> <replacement_file> --json
```

6. Re-run validation and lint on the self-hosted scope:

```bash
grace validate grace --json
grace lint grace --json
```

The same pattern applies to `apply-plan` for derived patch plans.

## Current Limits

- The current linter emits expected `large_block` warnings on several orchestration-heavy functions.
- Discovery on the repository root is still noisy because tests contain literal `@grace.*` strings in fixtures.
- The practical self-hosting scope is therefore the annotated `grace/` package, not the entire repository root.

## Rollout Status

- Wave 1: `parser`, `patcher`, `cli`
- Wave 2: `plan`, `validator`, `map`, `linter`

This establishes the first complete GRACE-native execution loop on the GRACE codebase itself.
