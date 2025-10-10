# Versioning & Dependency Management

This document defines the versioning strategy for ai-utils libraries, services, and dependencies. It serves as the single source of truth for version management across the monorepo.

## Semantic Versioning

### Package Versions

All libraries and services MUST use [Semantic Versioning 2.0.0](https://semver.org/):

```
vMAJOR.MINOR.PATCH
```

**Examples**: `v0.1.0`, `v1.2.3`, `v2.0.0-beta.1`

**Version Increments**:

- **MAJOR**: Breaking changes to public API
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

**Pre-1.0 Versions**:

- `0.y.z` versions indicate development/unstable APIs
- Breaking changes may occur in MINOR versions (e.g., `0.2.0` → `0.3.0`)
- Once stable, release `1.0.0` and follow semantic versioning strictly

### Git Tags

Tag all releases in Git:

```bash
# Tag format
git tag v0.1.0 -m "Release v0.1.0: Initial extractors library"

# Push tags
git push origin v0.1.0
```

**Tag Naming**:

- Library releases: `v0.1.0`
- Service releases: `service/rag-api/v0.1.0` (if versioned separately)
- Multi-module releases: Tag at monorepo root with release notes

### CHANGELOGs

Maintain a `CHANGELOG.md` for each library/service:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- New feature X

## [0.2.0] - 2024-10-10

### Added

- Feature Y with comprehensive tests

### Changed

- Improved performance of Z

### Fixed

- Bug in component W

## [0.1.0] - 2024-10-01

### Added

- Initial release
```

**Categories**:

- `Added` - New features
- `Changed` - Changes to existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Security fixes

## Dependency Management

### Dependency Constraints

Use **relaxed version constraints** to avoid dependency conflicts:

```toml
# ✅ Good - Relaxed constraints
[tool.poetry.dependencies]
pydantic = ">=2.5,<3.0"
structlog = ">=23.2,<25.0"
fastapi = ">=0.104,<1.0"

# ❌ Bad - Too restrictive
pydantic = "==2.5.0"
structlog = "^23.2.0"  # Can cause conflicts
```

**Guidelines**:

- Lower bound: Minimum tested version
- Upper bound: Next major version (exclusive)
- Format: `>=X.Y,<Z.0` where Z = X+1 for 0.x versions, or next major

### Version Alignment

**All libraries in the monorepo MUST use aligned dependency versions**:

```toml
# libs/extractors/pyproject.toml
pydantic = ">=2.5,<3.0"
structlog = ">=23.2,<25.0"

# libs/chunker/pyproject.toml
pydantic = ">=2.5,<3.0"  # ✅ Same as extractors
structlog = ">=23.2,<25.0"  # ✅ Same as extractors

# services/rag-api/pyproject.toml
pydantic = ">=2.5,<3.0"  # ✅ Same across all
structlog = ">=23.2,<25.0"  # ✅ Same across all
```

**Why**: Prevents version conflicts when libraries are used together.

### Lockfiles

**Always commit lockfiles** (`poetry.lock`, `package-lock.json`):

```bash
# Generate/update lockfile
poetry lock

# Install from lockfile (reproducible)
poetry install

# Commit lockfile
git add poetry.lock
git commit -m "chore: update dependencies"
```

**Benefits**:

- Reproducible builds across environments
- Pin transitive dependencies
- Detect dependency conflicts early

### Dependency Updates

**Regular dependency health checks**:

```bash
# Check for outdated dependencies
poetry show --outdated

# Update dependencies (respecting constraints)
poetry update

# Update specific package
poetry update pydantic

# Run tests after updates
poetry run pytest
```

**Schedule**: Weekly or bi-weekly dependency reviews.

**Process**:

1. Check for updates: `poetry show --outdated`
2. Review changelogs for breaking changes
3. Update one library at a time
4. Run full test suite
5. Test integration across modules
6. Commit with descriptive message

### Plugin & Adapter Versioning

For plugins and adapters (parsers, vector stores, embedding providers):

**Plugin Manifest**:

```python
class ParserManifest(BaseModel):
    name: str = "pdf"
    version: str = "1.0.0"  # Semantic version
    supported_types: List[str] = [".pdf"]
    schema_version: str = "1.0"  # Plugin API version
    dependencies: List[str] = ["pypdf>=3.0,<4.0"]
```

**Compatibility Matrix**:

Maintain compatibility information:

```markdown
## Compatibility

| Plugin Version | Core Version | Python | Notes          |
| -------------- | ------------ | ------ | -------------- |
| 1.0.x          | >=0.1,<0.2   | >=3.11 | Initial stable |
| 0.9.x          | >=0.1,<0.2   | >=3.11 | Beta           |
```

### Internal Library References

When one library depends on another in the monorepo:

```toml
# services/rag-api/pyproject.toml
[tool.poetry.dependencies]
# Development: path dependency
gundy-ai-extractors = {path = "../../libs/extractors", develop = true}
gundy-ai-chunker = {path = "../../libs/chunker", develop = true}

# Production: version dependency (once published)
# gundy-ai-extractors = ">=0.1,<0.2"
# gundy-ai-chunker = ">=0.1,<0.2"
```

**Signaling Stability**:

- `0.1.x` - Initial development, APIs may change
- `0.5.x` - Maturing, fewer breaking changes
- `1.0.x` - Stable, follows semantic versioning strictly

## Version Documentation

### In pyproject.toml

```toml
[tool.poetry]
name = "gundy-ai-extractors"
version = "0.1.0"  # Keep in sync with git tags
description = "Document extraction plugins"
```

### In Code

```python
# __init__.py
__version__ = "0.1.0"
```

### In API Responses

```python
# FastAPI
app = FastAPI(
    title="RAG API",
    version="0.1.0",  # Sync with package version
)

# Health endpoint
@app.get("/")
def root():
    return {
        "name": "RAG API",
        "version": "0.1.0",
        "libraries": {
            "extractors": "0.1.0",
            "chunker": "0.1.0",
            "embeddings": "0.1.0",
            "vectorstore": "0.1.0"
        }
    }
```

## Release Process

### Pre-Release Checklist

- [ ] All tests pass (`poetry run pytest`)
- [ ] Linter checks pass (`pre-commit run --all-files`)
- [ ] CHANGELOG.md updated
- [ ] Version bumped in `pyproject.toml` and `__init__.py`
- [ ] Documentation updated (README, API docs)
- [ ] Dependencies aligned across monorepo

### Release Steps

```bash
# 1. Update version
# Edit pyproject.toml, __init__.py, CHANGELOG.md

# 2. Commit version bump
git add -A
git commit -m "chore: bump version to v0.2.0"

# 3. Create tag
git tag v0.2.0 -m "Release v0.2.0

- Feature X added
- Bug Y fixed
- Performance improvements"

# 4. Push commit and tag
git push origin main
git push origin v0.2.0

# 5. (Optional) Publish to PyPI
poetry build
poetry publish
```

### Post-Release

- Update `[Unreleased]` section in CHANGELOG
- Announce release in team channels
- Update downstream projects if needed
- Monitor for issues

## Dependency Health

### Security Updates

```bash
# Check for security vulnerabilities
poetry run safety check

# Update vulnerable packages immediately
poetry update <package>
```

**Priority**: CRITICAL and HIGH severity vulnerabilities should be patched within 24-48 hours.

### Deprecation Notices

When deprecating features:

```python
import warnings

def old_function():
    warnings.warn(
        "old_function is deprecated and will be removed in v2.0. "
        "Use new_function instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # ... implementation
```

**Timeline**: Provide at least one MINOR version notice before removal in next MAJOR.

## Common Patterns

### Version Range Selection

```toml
# Core dependencies (stable)
python = ">=3.11,<3.13"
pydantic = ">=2.5,<3.0"

# Feature dependencies (optional)
chromadb = {version = ">=0.4,<1.0", optional = true}

# Dev dependencies (can be more flexible)
pytest = "^7.4"  # Latest 7.x
```

### Handling Version Conflicts

If dependency conflicts occur:

1. **Identify conflict**: `poetry install` will show incompatible versions
2. **Check constraints**: Review all `pyproject.toml` files
3. **Relax bounds**: Widen version ranges if safe
4. **Test thoroughly**: Ensure functionality with new versions
5. **Document**: Note version requirements in README

### Pre-release Versions

For beta/RC releases:

```toml
version = "1.0.0-beta.1"
version = "1.0.0-rc.2"
version = "1.0.0"  # Stable release
```

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [PEP 440 - Version Identification](https://peps.python.org/pep-0440/)

## Summary

**Key Principles**:

1. ✅ Use semantic versioning (`vMAJOR.MINOR.PATCH`)
2. ✅ Use relaxed constraints (`>=X.Y,<Z.0`)
3. ✅ Align versions across monorepo
4. ✅ Commit lockfiles
5. ✅ Maintain CHANGELOGs
6. ✅ Tag all releases in Git
7. ✅ Test dependency changes
8. ✅ Document version requirements
9. ✅ Regular dependency health checks
10. ✅ Security updates prioritized
