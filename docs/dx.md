## Developer Experience (DX)

### Linting & Formatting

- Python: `ruff` (lint), `black` (format), `mypy` (types) when applicable.
- TS/JS: `eslint` + `prettier` + `tsc --noEmit` for type checking.

### Pre-commit Hooks

- Use `pre-commit` (Python) and `lint-staged` (Node) to enforce:
  - Lint, format, tests, and basic security checks before push.

### CI/CD

- GitHub Actions matrix per module:
  - Install deps, lint, typecheck, test.
  - Optional: auto-publish to PyPI/npm on version tags.

### Docs

- Start simple: `mkdocs` (Python) or minimal Docusaurus/Next docs site.
- Optionally mirror Notion → GitHub Pages export for quick sharing.
