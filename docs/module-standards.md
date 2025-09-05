## Module Standards

These standards ensure every module in this repo can be installed directly from Git and published to package registries.

### Goals

- **Python modules** are installable via `pip` and follow modern packaging.
- **TypeScript/JavaScript packages** are installable via `npm` and work with monorepo workspaces.
- Modules can be consumed directly from GitHub for rapid client integration.

See also: `starter-templates.md`, `dx.md`, `versioning.md`, `security-privacy.md` for complementary guidance.

### Python

- **Packaging**: Use `pyproject.toml` with Poetry for dependency management and builds.
  - Required files: `pyproject.toml`, `README.md`, `LICENSE`, and module source under `src/`.
  - Example project layout:
    - `src/gundy_ai/<module_name>/...`
    - Tests in `tests/` using `pytest`.
- **Namespace packages**: Use the `gundy_ai` namespace (PEP 420 style) such as:
  - `gundy_ai.data`, `gundy_ai.prompts`, `gundy_ai.eval`, etc.
  - Do not include an `__init__.py` at the namespace root if using implicit namespace packages.
- **Typing**: Ship type hints. Include a `py.typed` file in the package root to indicate typed package.
- **Publishing**: Build with `poetry build`; publish to internal or public index as needed.
- **Install from Git**: Support installs like:
  - `pip install git+https://github.com/gundy27/ai-utils.git#subdirectory=libs/<python_module_dir>`
    - Ensure the target subpackage is independently buildable and has its own `pyproject.toml`.

### TypeScript / JavaScript

- **Workspaces**: Use `pnpm` or `yarn` workspaces for the monorepo.
  - Each package has its own `package.json` with `name`, `version`, `main`, `types`, and `files` entries.
  - Prefer `pnpm` for efficient installs and isolated dependency graphs.
- **Build tooling**: Recommend `tsup` or `tsc` to emit ESM+CTS where appropriate.
  - Emit types with `declaration: true` and include `types` in `package.json`.
- **Publishing**: Configure for private/public publication to npm.
  - Public: omit `"private": true` and set `publishConfig.access` as needed.
  - Private (Git-only consumption) is fine; ensure `prepare` builds on install if needed.
- **Install from GitHub**: Support installs like:
  - `npm install github:gundy27/ai-utils#path=libs/<js_package_dir>`
  - or via protocol: `npm install git+https://github.com/gundy27/ai-utils.git#libs/<js_package_dir>`

### Repo-level Expectations

- Each module (Python or TS/JS) lives in a clearly scoped subdirectory under `libs/` or `templates/`.
- Include `README.md` in each module describing:
  - Purpose, quick start, API surface, and versioning policy.
- Add minimal CI checks (lint, typecheck, test) per module when feasible.
- Tag versions when publishing; follow SemVer.
- Align with DX standards: lint/format, pre-commit hooks, and CI (see `dx.md`).
- Respect security practices: env-based config, secret hygiene (see `security-privacy.md`).

### Quick Reference

- Python (git install):
  - `pip install git+https://github.com/gundy27/ai-utils.git#subdirectory=libs/<python_module_dir>`
- Node (GitHub shorthand):
  - `npm install github:gundy27/ai-utils` (use `#path=...` to target a specific package)

If you add a new module, ensure it conforms to the above so clients can consume it immediately via Git or published registries.
