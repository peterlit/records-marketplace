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

## 0.4.1 — 2026-09-02

- **`records-export-doc`** — renders any project file as a formatted Google Doc on
  demand, for taking to an appointment or sharing. Kept from the reverted 0.5.x work,
  where it was bundled with the link-style experiment but is independent of it.
  The skill is explicit that the Doc is a **dated snapshot, never the record**: Docs
  cannot be edited through the connector, and on the Drive mount they are ~170-byte
  pointers — invisible to grep, to Obsidian, and to snapshots.

## 0.5.0 — 2026-09-02

*(Version 0.5.x was previously used for a link-style experiment that was reverted;
this is unrelated work reusing the number.)*

- **Provider profiles as data** — `templates/providers/{gdrive,dropbox,icloud,onedrive,local}.json`
  carry each provider's mount caveats, offline-mode requirement, conflict-copy patterns,
  connector capabilities and hazards. `--provider` replaces free-text `--cloud` (kept as an
  alias). The generated `CLAUDE.md` now warns about the hazards that actually apply: the
  symlink requirement and .gdoc pointers for Drive, 0-byte eviction and no-connector-fallback
  for iCloud, nothing at all for local.
- **Vaults describe themselves** — `.records-project.json` records preset, provider, shared
  mode, co-users, decision-maker, Obsidian and snapshot settings, plugin version, and the
  provider's conflict patterns. `validate_vault.py` reads it instead of OR-ing every
  provider's patterns together, which over-matched.
- **`--reconfigure`** — move a vault between providers by rewriting only `CLAUDE.md` and
  `.records-project.json`. **No content is touched**, verified by hashing all 29 files
  across a migration. Refuses to run without an existing config so it cannot be mistaken
  for a fresh scaffold over live data. All 20 provider-pair migrations pass.
- **Fixed a validator false positive**: OneDrive's conflict pattern flagged
  `Settled — do not re-open.md` (it ends `-open.md`). Tightened, and scoped with `(?-i:...)`
  because the validator compiles with `re.I`, which had defeated the uppercase check.
  OneDrive detection is documented as best-effort — machine-name suffixes are not reliably
  distinguishable from ordinary hyphenated filenames.

## 0.6.0 — 2026-09-02

- **Triggering eval corpus** (`evals/evals.json`, skill-creator schema) — 18 prompts
  across all 7 skills, including **5 near-miss negatives** that must fire nothing:
  "organise my Downloads", "export this spreadsheet as a PDF", "review this PR and tell
  me what I'm missing". Negatives are usually what an eval set is missing, and they are
  what catches a description that fires on a keyword rather than a situation.
- **`lint_triggering.py`** — static proxy flagging two failure classes: two skills
  competing for the same prompt, and a negative prompt scoring high against a skill.
  ⚠️ Documented in the script itself as **not a measure of triggering** — that needs
  Claude in the loop via skill-creator's `run_eval.py`.
- **Fixed a real description gap it found**: `file-to-records` shared **zero vocabulary**
  with "the cardiologist just called and changed the dose" — a core use case. Widened to
  cover verbal reports, medication and dose changes, symptoms appearing, and decisions
  being made, not just files landing in the Inbox.
