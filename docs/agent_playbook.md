# Agent Playbook

GRACE is intended for shell-driven agents that need deterministic repository editing rather than prompt-only code generation.

This playbook defines the canonical workflow and the baseline eval expectations for agents operating on GRACE-native repositories.

## Canonical Loop

The standard loop is:

`map -> query -> read -> impact -> plan -> apply-plan -> validate -> lint`

The recommended commands are:

```bash
grace map grace --json
grace query anchors grace --json
grace read grace <anchor_id> --json
grace impact grace <anchor_id> --json
grace plan impact grace <anchor_id> --json
grace apply-plan plan.json --dry-run --preview --json
grace apply-plan plan.json --json
grace validate grace --json
grace lint grace --json
```

## Operating Rules

- Treat inline GRACE annotations as the only source of truth.
- Select targets by `anchor_id`, never by line number.
- Use `plan impact` as a proposal surface, not as an executable change by itself.
- Prefer atomic anchor-driven patches over whole-file rewrites.
- Treat `validate` as blocking and `lint` as advisory unless a project policy says otherwise.

## Self-Hosted Scope

For GRACE itself, the canonical scope is the annotated `grace/` package.

This keeps discovery deterministic and avoids dragging tests or unrelated fixtures into the active editing surface.

## Suggested Flows

### Codex / shell-driven agents

Use the CLI directly and consume `--json` output as the machine contract.

### Claude Code / shell-driven agents

Use the same GRACE CLI loop; no IDE-specific integration is required.

### Human-in-the-loop agents

Always surface `--preview` output before write steps.

## Baseline Evals

The baseline self-hosted eval suite on `grace/` measures:

- anchor selection accuracy
- patch/apply-plan success rate
- rollback rate
- unnecessary file touch rate

These evals are intentionally simple. They are meant to measure workflow stability and contract correctness, not model intelligence.

## Current Baseline Scenarios

- read + impact + plan for `grace.map.build_file_map`
- read + impact + plan for `grace.query.query_neighbors`
- dry-run patch for `grace.map.build_file_map`
- dry-run apply-plan for `grace.map.build_file_map`

The baseline expectation is:

- anchor selection accuracy = `1.0`
- patch/apply-plan success rate = `1.0`
- rollback rate = `0.0`
- unnecessary file touch rate = `0.0`
