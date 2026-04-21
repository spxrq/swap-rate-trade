# Changelog

All notable structural changes and decisions get a short entry here.

## [Unreleased]

### Added
- Initial scaffold: `synthetic/want/`, `synthetic/dont_want/`, `notebooks/`, `tests/`.
- Docs: `DATA_CONTRACT.md`, `DGP_CATALOG.md`, `BQUANT_COMPAT.md`, `IMPLEMENTATION_STATUS.md`.
- Packaging via `pyproject.toml` + `requirements.txt` (editable install makes `synthetic` importable from anywhere).
- `nbstripout` pre-commit hook to keep notebook outputs out of git.
- `CLAUDE.md` project-specific instructions.

### Archived
- Original `nb0`–`nb5` template + README moved to `archive/template_reference/` for reference only.
