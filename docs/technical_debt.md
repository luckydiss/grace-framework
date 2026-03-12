# Technical Debt

## Known Limitations

- Python is the only supported inline annotation surface in v1.
- CLI is intentionally minimal and shell-oriented.
- The parser, validator, and linter are file/project model layers, not full repository analysis tools.
- Patcher is single-file and single-block only.
- Apply-plan is sequential only; it does not provide transactional all-or-nothing execution.
- Repo graph is currently exposed through the existing map contract; there is no separate graph module or richer graph schema yet.

## Non-Goals

- Sidecar-first workflows
- Line-number-based patching
- Multi-file transactional patch orchestration
- Graph analytics and query engines
- Auto-generation or planning flows
- IDE/editor integration

## Backlog For v2

- Language-agnostic frontends beyond Python
- Stronger repository-wide semantic analysis
- Transactional patch application and richer plan operations
- Richer graph export and graph analytics
- Better packaging polish and release automation
