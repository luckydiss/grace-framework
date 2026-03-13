# v1.0 Readiness Review

This document records the current readiness assessment for GRACE after the protocol freeze, adapter hardening, and repo-scale reliability milestones.

It is not a promise that `v1.0` should be cut immediately.

Its job is to answer:

- what is already stable enough for `v1.0`
- what is still intentionally provisional
- what must be resolved before GRACE should call itself a stable agent development platform

## Review Scope

The current review covers:

- source-of-truth invariants
- CLI / JSON protocol surface
- self-hosted workflow
- patch/apply-plan execution discipline
- release criteria and repo-scale reliability gates
- language adapter architecture
- adapter maturity status

## What Is Ready

The following parts of GRACE now behave like a stable platform baseline:

### 1. Source-of-truth model

- inline annotations remain the only source of truth
- semantic identity is still `module_id` + `anchor_id`
- derived layers remain read-only and secondary

### 2. Core semantic pipeline

- parser
- validator
- linter
- map
- query
- impact
- read
- planner
- patcher
- apply-plan

These layers are all covered by the current test matrix and self-hosted usage.

### 3. Shell-driven agent contract

The CLI now has:

- stable machine-readable `--json` output
- deterministic project/file scope behavior
- explicit repository-root policy
- dry-run and preview support for patch/apply-plan

### 4. Self-hosted development loop

The GRACE-on-GRACE workflow is established:

`map -> query -> read -> impact -> plan -> apply-plan -> validate -> lint`

This is no longer a conceptual workflow only; it is part of the documented and tested baseline.

### 5. Adapter architecture

The adapter boundary is no longer hypothetical:

- Python reference adapter
- TypeScript pilot adapter
- Go pilot adapter

This is enough to say the core architecture scales beyond a single language.

## What Is Still Not Ready For v1.0

The following items are still blockers or at least strong reasons not to cut `v1.0` yet.

### 1. Pilot adapters remain pilot adapters

TypeScript and Go are intentionally narrow.

That is acceptable for `0.x`, but `v1.0` should not overstate adapter maturity while two non-reference adapters are still explicitly pilot-tier.

### 2. Repository-root validation is intentionally non-green

`parse . --json` and `map . --json` are valid export surfaces.

But:

- `validate . --json`
- `lint . --json`

are intentionally not clean because parity fixtures reuse semantic identities across languages.

This is documented and correct, but it means repository-root behavior still requires explanation rather than being trivially intuitive.

### 3. Artifact policy is documented, but not enforced by tooling

We now document committed vs local-only derived artifacts, but GRACE itself does not yet enforce artifact hygiene.

That is manageable, but it is still a process-level discipline rather than a fully encoded policy.

### 4. Release messaging still needs a final pass

The protocol is much more stable than before, but a final `v1.0` release would still need:

- a narrower public promise
- an explicit statement about adapter tiers
- a release note that distinguishes stable core from pilot frontends

## Current Recommendation

Current recommendation:

**Do not cut `v1.0` yet.**

Instead:

- keep the core and CLI protocol on the current hardening track
- treat Python as the stable baseline
- keep TypeScript and Go clearly labeled as pilot adapters
- perform one more stabilization pass focused on release messaging and artifact hygiene

## Proposed Next Step

The next step after this review should be:

## v0.21 - v1.0 Release Prep

Focus:

- final release-surface audit
- release messaging cleanup
- artifact policy cleanup
- final baseline export and release notes

This should still avoid new runtime semantics.

## Current Status Summary

### Ready now

- source-of-truth model
- semantic editing discipline
- self-hosted workflow
- shell-driven agent contract
- repo-scale export reliability
- adapter architecture

### Not yet release-final

- pilot adapter maturity
- repository-root validation expectations
- artifact hygiene as a tooling-enforced policy
- final `v1.0` release framing
