# Polyglot Annotation Contract

This document fixes the annotation vocabulary and comment-host policy that future GRACE frontends must preserve.

It is a specification track document. It does not imply that current runtime parsers already support every syntax form listed here.

## Core Rule

GRACE semantics are universal.

Frontend syntax is language-specific only in how annotations are hosted inside comments.

The annotation vocabulary itself must remain stable across frontends.

## Vocabulary Invariants

The following annotation names are canonical:

- `@grace.module`
- `@grace.purpose`
- `@grace.interfaces`
- `@grace.invariant`
- `@grace.anchor`
- `@grace.complexity`
- `@grace.belief`
- `@grace.links`

Frontend implementations must not rename these annotations.

## Comment-Host Syntax Policy

Acceptable comment-hosted forms to preserve semantically:

- `# @grace.anchor billing.pricing.apply_discount`
- `// @grace.anchor billing.pricing.apply_discount`
- `-- @grace.anchor billing.pricing.apply_discount`
- `/* @grace.anchor billing.pricing.apply_discount */`
- `<!-- @grace.anchor billing.pricing.apply_discount -->`

Canonical rule:

- the host comment syntax may vary
- the embedded GRACE annotation token sequence must remain semantically identical

## Whitespace And Payload Rules

- Annotation names are case-sensitive.
- The canonical prefix is exactly `@grace.`.
- A payload begins after at least one whitespace character following the annotation name.
- Leading and trailing whitespace around payload values is not semantically significant.
- Empty payloads are invalid for required text-bearing annotations.
- `grace.links` uses comma-separated anchor ids.
- Whitespace after commas in `grace.links` is allowed and non-semantic.
- Frontends must normalize payload text the same way current GRACE models expect:
  trimming surrounding whitespace without rewriting meaningful inner text.

## Payload Semantics

- `grace.module`, `grace.anchor`, and `grace.links` carry identity-bearing values.
- `grace.purpose`, `grace.interfaces`, `grace.invariant`, and `grace.belief` carry descriptive text.
- `grace.complexity` carries an integer semantic value.

These meanings must not change between frontends.

## Multiline Policy

The current baseline assumes single-line annotations.

Future frontends may support multiline comment hosts, but they must project back into the same logical annotation model without inventing new source-of-truth semantics.

## Frontend-Readiness Constraints

Any future frontend must be able to:

- find GRACE annotations inside the supported comment syntax of its language
- bind annotations to semantic entities in that language
- determine block kind
- compute block span
- emit a `GraceFileModel`-compatible result

The core layer remains responsible for:

- validator semantics
- linter policy
- derived map and graph artifacts
- patch plans
- CLI JSON contract

## Non-Goals

This document does not:

- add runtime multi-language support by itself
- define sidecar-first behavior
- replace the code-first source-of-truth model
- authorize line-based coordinates as semantic identity
