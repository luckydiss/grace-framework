# Bootstrap Safety Matrix

GRACE `v1.5` adds a deterministic bootstrap safety report layer.

## Purpose

Language packs, file policy, adapter probe, and construct packs answer pieces of the onboarding question.

Bootstrap safety answers the full operational question:

- can this file or repository be bootstrapped safely right now?
- how many files are immediately safe for scaffold apply?
- which files still block bootstrap apply?
- why are they blocked?

## Command

```bash
grace adapter safety path/to/repo
```

## Safety model

Bootstrap safety is derived from:

- file-policy verdicts
- language-pack and construct-pack routing
- bootstrap candidate discovery rules

It does not:

- patch files
- invent semantics
- weaken parser rules
- override repository policy

## Issue kinds

- `preview_only`
- `unsupported`
- `ignored`
- `blocked_safe_apply`

`blocked_safe_apply` means the file looked safe from policy alone, but bootstrap candidate discovery still excluded it.

## Intended use

Recommended onboarding loop for unfamiliar repositories:

1. `grace adapter gaps <path>`
2. `grace adapter safety <path>`
3. extend file policy or construct packs if needed
4. rerun `grace adapter safety <path>`
5. start `grace bootstrap --apply`
