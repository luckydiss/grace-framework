# Technical Debt

## Known Limitations

- Python is the only supported inline annotation surface in v1.
- CLI is intentionally minimal and shell-oriented.
- The parser, validator, and linter are file/project model layers, not full repository analysis tools.
- Patcher is single-file and single-block only.
- Patch workflow is still single-operation oriented; patch plans do not exist yet.
- Cross-file `grace.links` are still constrained by the current parser's file-local link resolution baseline.

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
- Multi-file patch plans and transactional patch application
- Richer graph export and graph analytics
- Better packaging polish and release automation
