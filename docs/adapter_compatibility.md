# Adapter Compatibility Matrix

This matrix records current GRACE adapter coverage after the TypeScript pilot, the Go adapter milestone, and the v0.14 hardening work.

| Feature | Python | TypeScript | Go |
| --- | --- | --- | --- |
| Module annotations | Supported | Supported | Supported |
| Function declarations | Supported | Supported | Supported |
| Async functions | Supported | Supported | Not applicable |
| Class declarations | Supported | Supported | Struct type declarations only |
| Methods | Supported | Supported | Supported |
| Arrow functions | Not applicable | Unsupported | Not applicable |
| Function expressions | Unsupported | Unsupported | Unsupported |
| Object methods | Unsupported | Unsupported | Not applicable |
| JSX / TSX | Not applicable | Unsupported | Not applicable |
| Interface declarations as semantic blocks | Not applicable | Not applicable | Unsupported |

## Notes

- Python remains the reference implementation.
- TypeScript remains a pilot adapter with deliberately narrow syntax coverage.
- Go remains a pilot adapter with deliberately narrow function/method plus struct-type coverage.
- Unsupported constructs must not break parsing if they do not contain GRACE annotations.
- If GRACE annotations target an unsupported construct and no supported semantic entity can bind them, parsing must fail predictably.

## Adapter Quality Matrix

| Adapter | Status | Parity Coverage | Conformance | Notes |
| --- | --- | --- | --- | --- |
| Python | Reference | Basic + async-shape + service-shape + links-shape | Stable | Normative baseline for adapter behavior. |
| TypeScript | Pilot | Basic + async-shape + service-shape + links-shape | Stable | Narrow runtime coverage; unsupported arrow/function-expression bindings fail predictably. |
| Go | Pilot | Basic + async-shape equivalent + service-shape + links-shape | Stable | Async parity is represented by a regular-function equivalent; interface blocks remain unsupported. |

## Support Tier Policy

GRACE uses three support tiers for adapters:

| Tier | Meaning | Requirements |
| --- | --- | --- |
| Reference | Normative baseline for adapter behavior | broadest docs coverage, conformance, parity, eval stability |
| Pilot | Narrow but honest runtime support | explicit unsupported syntax list, conformance, parity, eval coverage |
| Experimental | Boundary proof only | not yet a contract baseline; may lack full parity/eval coverage |

Current status:

- Python = Reference
- TypeScript = Pilot
- Go = Pilot

## Multi-Language Behavior Guarantees

Across Python, TypeScript, and Go adapters, GRACE guarantees:

- inline GRACE annotations remain the only source of truth
- adapters emit `GraceFileModel`-compatible normalized output
- deterministic block ordering for equivalent file contents
- stable parse behavior on unsupported syntax:
  - inert when unsupported constructs are unannotated
  - predictable parse failure when annotations target unsupported constructs
