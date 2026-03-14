# External Specs

GRACE can load language and construct packs from external TOML files.

Built-in specs live under:

- `grace/specs/languages/*.toml`
- `grace/specs/constructs/<language>/*.toml`

Repository-local specs can be placed under:

- `.grace/specs/languages/*.toml`
- `.grace/specs/constructs/<language>/*.toml`

Additional spec directories can be configured in `pyproject.toml` under `[tool.grace.specs]`.
