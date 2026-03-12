# GRACE Open Decisions

These items are intentionally unresolved and should be treated as tracked design decisions rather than accidental omissions.

## Semantic boundaries

- What counts as a "significant block" across languages?
- When should a branch or local block receive its own anchor?

## Stability rules

- When is anchor rename allowed versus treated as semantic replacement?
- How should anchor identity survive extracted-function refactors?

## Contract scope

- Should contracts eventually include effects, latency, and error semantics?
- Should contracts be embeddable inline for generated code scenarios?

## BELIEF_STATE policy

- Can complexity be auto-detected?
- What minimum evidence is required for risks and failure modes?

## Tooling scope

- Should semantic patching first output a patch plan or directly mutate code?
- Should graph export be language-agnostic from day one or grow per language?
