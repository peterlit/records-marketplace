# Changelog

## 0.2.0 — 2026-08-08

- `file-to-records` — the intake loop: event-date filing, original archived first,
  duplicate and better-scan detection, conflicting trend values flagged not overwritten.
- `records-gap-audit` — full re-read; checks the settled register and later documents
  before raising anything; "no new gaps" is a valid result.
- `records-critique` — steelman for / strongest case against; distinguishes *wrong*
  from *one reasonable option* from *outside mainstream*; never ends with "you should".
- `snapshot.py` — builds in scratch then copies (the `zip` rename failure on cloud
  mounts), verifies the landed size, excludes 0-byte cloud-only files.

## 0.1.0 — 2026-08-08

- `bootstrap-records-project` — interview then build.
- `scaffold.py`, `validate_vault.py`, `lint_frontmatter.py`, `lint_privacy.py`, `probe.py`.
- `health` and `generic` presets; core templates with a `{{VAR}}` / `{{#if}}` renderer.
- Established: never hardcode a plugin path in shell; resolve via `__file__`.
