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

## 0.3.0 — 2026-09-02

- **Shared mode.** `--co-user` (repeatable); two or more switches the engine into
  equal-co-user mode: no operator/contributor split, memory is per-account and
  therefore not a source of truth, read the Prompt Log at session start, attribute
  everything, merge rather than overwrite in `01 Master`. Prompt Log gains a Who column.
- **Fixed the plugin locator.** Marketplace installs mount at
  `.remote-plugins/<opaque-id>/`, not `.claude/skills/`. The previous locator was
  written against built-in skills and would have failed on every real install.
- **Corrected the deletion guidance.** The block is *Cowork's* protection, not the
  cloud provider's — it applies to ordinary local disks too. Call
  `allow_cowork_file_delete`; the Drive connector's `trash_file` is a fallback.
- **`validate_vault.py` no longer passes a folder that doesn't exist** (it printed
  `vault valid` after checking zero notes), and fails when no markdown is found.
- Template renderer handles nested `{{#if}}`; unrendered template syntax now fails
  validation instead of shipping.

## 0.4.0 — 2026-09-02

- **In-folder memory.** `MEMORY.md` index + `memory/<topic>.md` files, created in every
  vault. The engine reads them at session start and treats them as the source of truth:
  Claude's account memory is per-user and diverges, so anything load-bearing lives here.
  One topic per file, because a single memory file is a guaranteed collision point.
- **Presence markers (shared mode).** `_sync/<ISO>__<who>__started|stopped.md` —
  creation-only, uniquely named, so concurrent sessions cannot collide. New
  `records-sync-status` skill and `sync_status.py` report ACTIVE / STALE (>4h) sessions.
  Documented throughout as **awareness and audit, never a lock** — sync latency makes
  them unreliable over exactly the window a lock would matter.
- **Optimistic concurrency.** The engine now requires re-reading a curated `01 Master`
  file immediately before writing it, and merging rather than overwriting if it changed.
  This is what actually makes concurrent editing safe; the markers only make collisions
  rarer and visible.
