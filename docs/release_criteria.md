# Release Criteria

This document records the current release gates for GRACE while the project is still converging toward a stable agent development platform.

The purpose is simple:

- make hardening work measurable
- make releases comparable
- keep GRACE focused on protocol reliability rather than feature sprawl

## Core Principle

GRACE releases should be gated by deterministic protocol behavior, not by the number of exposed commands or adapters.

## Minimum Release Gates

The following gates must pass before a hardening milestone is treated as ready:

### 1. Full test suite

- `python -m pytest -q` passes

### 2. Self-hosted validation

- `grace validate grace --json` succeeds
- `grace lint grace --json` succeeds

### 3. Repository export stability

- `grace parse . --json` succeeds
- `grace map . --json` succeeds
- repeated runs of repo-root parse/map are deterministic

### 4. Curated-scope validation policy

The following scopes should validate cleanly:

- `grace/`
- `examples/basic`
- `examples/go`
- `examples/typescript`
- `examples/parity/python`
- `examples/parity/typescript`
- `examples/parity/go`

Repository-root `validate . --json` is not currently a release gate because parity fixtures intentionally reuse semantic identities across languages.

### 5. Agent workflow reliability

The canonical self-hosted loop should remain stable:

`map -> query -> read -> impact -> plan -> apply-plan --dry-run -> validate -> lint`

### 6. Patch discipline

Patch/apply-plan behavior should preserve:

- anchor selection correctness
- no unnecessary file touches
- no rollback on known-good dry-run scenarios
- rollback on invalid real write scenarios where parse/validate fail

## Current Baseline Metrics

Current hardening milestones target:

- `anchor_selection_accuracy = 1.0`
- `patch_apply_plan_success_rate = 1.0`
- `rollback_rate = 0.0` on known-good dry-run scenarios
- `unnecessary_file_touch_rate = 0.0`
- `deterministic_cli_contract_rate = 1.0`
- `repo_root_export_success_rate = 1.0`
- `curated_scope_validation_rate = 1.0`

## Non-Gates

The following are intentionally not release gates for the current phase:

- adding a new language
- broader syntax coverage for pilot adapters
- UI / IDE integration
- ranking heuristics
- domain profiles
- source-of-truth expansion

## How To Use This Document

Use this document together with:

- `docs/protocol_freeze.md`
- `docs/agent_playbook.md`
- `tests/test_agent_evals.py`
- `tests/test_protocol_freeze.py`
- `tests/test_repo_reliability.py`

If a future change adds a capability but weakens these gates, the capability is not ready yet.
