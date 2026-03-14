# Adapter Compatibility Matrix

This matrix records current GRACE adapter coverage after the TypeScript pilot, the Go adapter milestone, the v0.14 hardening work, and the shared data-driven adapter consolidation.

| Feature | Python | TypeScript | Go |
| --- | --- | --- | --- |
| Module annotations | Supported | Supported | Supported |
| Function declarations | Supported | Supported | Supported |
| Async functions | Supported | Supported | Not applicable |
| Class declarations | Supported | Supported | Struct type declarations only |
| Methods | Supported | Supported | Supported |
| Arrow functions | Not applicable | Supported | Not applicable |
| Function expressions | Unsupported | Unsupported | Unsupported |
| Object methods | Unsupported | Supported | Not applicable |
| JSX / TSX | Not applicable | Unsupported | Not applicable |
| Interface declarations as semantic blocks | Not applicable | Not applicable | Unsupported |
| Bootstrap discovery | Supported via shared Tree-sitter base | Supported via shared Tree-sitter base | Supported via shared Tree-sitter base |

## Notes

- Python remains the reference implementation.
- TypeScript remains a pilot adapter with deliberately narrow syntax coverage.
- Go remains a pilot adapter with deliberately narrow function/method plus struct-type coverage.
- Python, TypeScript, and Go now reuse a shared Tree-sitter execution engine with language-specific declarative specs.
- Unknown suffixes route through a deterministic fallback adapter instead of failing adapter lookup immediately.
- Bootstrap scaffolding relies on the same adapter boundary: supported languages expose unannotated block discovery through the shared base, while unsupported suffixes fall back to deterministic text discovery.
- Unsupported constructs must not break parsing if they do not contain GRACE annotations.
- If GRACE annotations target an unsupported construct and no supported semantic entity can bind them, parsing must fail predictably.

## Adapter Quality Matrix

| Adapter | Status | Parity Coverage | Conformance | Notes |
| --- | --- | --- | --- | --- |
| Python | Reference | Basic + async-shape + service-shape + links-shape | Stable | Normative baseline for adapter behavior. |
| TypeScript | Pilot | Basic + async-shape + service-shape + links-shape | Stable | Supports function declarations, arrow functions, classes, and object literal methods; function expressions remain unsupported. |
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
