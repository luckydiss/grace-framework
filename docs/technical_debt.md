# Technical Debt

## Known Limitations

- Python is the reference adapter, while TypeScript and Go remain limited pilot adapters rather than broad language support.
- CLI is intentionally minimal and shell-oriented.
- The parser, validator, and linter are file/project model layers, not full repository analysis tools.
- Patcher is single-file and single-block only.
- Patcher canonicalizes target paths to absolute filesystem paths early in execution, so machine-readable patch results should be treated as canonical-path outputs rather than preserving the caller's original relative spelling.
- Repo graph is currently exposed through the existing map contract; there is no separate graph module or richer graph schema yet.
- Repository-root validation now depends on `[tool.grace]` scope hygiene; keeping default include/exclude rules aligned with the real development scope remains an ongoing maintenance task.
- Committed `.plan.json` and `.pyfrag` example files remain lint-visible by design; `grace clean` only removes deterministic temp artifacts and does not rewrite repository examples.

## Non-Goals

- Sidecar-first workflows
- Line-number-based patching
- Graph analytics and query engines
- Auto-generation or planning flows
- IDE/editor integration

## Backlog For v2

- Language-agnostic frontends beyond Python
- Stronger repository-wide semantic analysis
- Richer plan operations beyond `replace_block`
- Richer graph export and graph analytics
- Better packaging polish and release automation
