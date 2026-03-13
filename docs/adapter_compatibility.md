# Adapter Compatibility Matrix

This matrix records current GRACE adapter coverage after the TypeScript pilot and v0.14 hardening work.

| Feature | Python | TypeScript |
| --- | --- | --- |
| Module annotations | Supported | Supported |
| Function declarations | Supported | Supported |
| Async functions | Supported | Supported |
| Class declarations | Supported | Supported |
| Methods | Supported | Supported |
| Arrow functions | Not applicable | Unsupported |
| Function expressions | Unsupported | Unsupported |
| Object methods | Unsupported | Unsupported |
| JSX / TSX | Not applicable | Unsupported |

## Notes

- Python remains the reference implementation.
- TypeScript remains a pilot adapter with deliberately narrow syntax coverage.
- Unsupported constructs must not break parsing if they do not contain GRACE annotations.
- If GRACE annotations target an unsupported construct and no supported semantic entity can bind them, parsing must fail predictably.
