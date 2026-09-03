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

- **Triggering eval corpus** (`evals/evals.json`, skill-creator schema) — 22 prompts across
  all 7 skills, **9 of them near-miss negatives** that must fire nothing: "organise my
  Downloads", "export this spreadsheet as a PDF", "review this PR and tell me what I'm
  missing", "help me organize my tax documents", "clear my email backlog". Negatives are
  what an eval set usually lacks and what catches a description firing on a keyword
  rather than a situation. Feed this to skill-creator's `run_eval.py`.
- **`file-to-records` description widened** — it shared *zero* vocabulary with "the
  cardiologist just called and changed the dose", a core use case. Now covers verbal
  reports, medication and dose changes, symptoms and decisions, not only files arriving.
- **`bootstrap-records-project` is explicit-invocation-only.** First narrowed (ongoing
  situation + advisors + a DO NOT USE clause), then taken all the way: the description now
  tells the model never to select it on its own initiative. Rationale — a project is
  bootstrapped once or twice a year against hundreds of unrelated chats, so the expected
  cost of a false positive dwarfs the convenience of a natural-language trigger. Nothing is
  lost: inside a project the generated `CLAUDE.md` runs the workflow. Evals 1–3 were flipped
  from positives to negatives to lock this in.
- **The other skills are scoped to inside-a-project**, not silenced. `file-to-records`,
  `records-critique` and `records-gap-audit` still fire automatically — but only where a
  `CLAUDE.md` + `01 Master/` or `.records-project.json` says a project exists. The generated
  `CLAUDE.md` gained a **Skills table** naming each one against its trigger, so filing is
  driven by the folder rather than by a description happening to match the user's wording.
  It also states that if the plugin is absent, the steps are written out inline and must be
  done anyway — a project whose filing silently stops because a plugin was uninstalled would
  be worse than no plugin.
- **Removed `lint_triggering.py`.** A static word-overlap analyzer was built and then
  deleted the same day. It found one real bug, but tuning it three times produced
  contradictory guidance, and it ended up ranking `records-sync-status` — a skill about
  presence markers — top for "my mother was just diagnosed". Word overlap measures
  vocabulary, not meaning, and it cannot see negation at all: adding "DO NOT USE for
  clearing an email backlog" made the tool report the skill as *more* likely to fire on
  that phrase. **A metric that inverts on a correct fix is worse than no metric**, because
  it invites optimising against noise. Triggering needs Claude in the loop; there is no
  cheap proxy.

## 0.7.0 — 2026-09-02

- **`--language`: structure in English, prose in the user's language.** A records project
  can now be kept in any language. The choice is written to `.records-project.json` *and*
  to a `## Language` section in the generated `CLAUDE.md` — which is the point. Asking
  during the interview is not enough; a later session starts with no memory of that
  conversation and silently reverts to English. Folder and file names stay English because
  `scaffold.py`, `validate_vault.py`, the snapshot trigger and the skill descriptions all
  match those exact strings.
- **Bootstrap Step 0 — ask, don't guess.** If the person writes in another language, ask
  once *in their language* whether to keep the project in it. Previously nothing anywhere
  handled language; Claude sometimes mirrored the user and sometimes didn't, which read as
  an intermittent bug rather than the absent feature it was.
- **Bootstrap Step 2b — translate the seeded prose.** Templates render in English, so a
  non-English vault was landing with English folder notes and START HERE: the person's
  first look at their own project in the wrong language. Now translated in place, with a
  never-translate list — file and folder names, anything inside `[[ ]]` *including the
  alias after the pipe*, anything backticked, and quoted source material. `CLAUDE.md`
  translation is opt-in: it is the engine, so a mistranslation changes behaviour rather
  than wording.
- **Validator catches language drift.** If the config says a language but `CLAUDE.md` has
  no matching `## Language` section, validation fails — because the failure mode is silent
  and only becomes visible after months of records have accumulated in the wrong language.
- **`preflight.py` — fail in two seconds, not fifteen minutes.** Writes a canary into the
  target, reads it back, checks it is non-zero, deletes it. Catches an unmounted path, a
  cloud folder in streaming mode (0-byte writes that report success), a mangling sync layer,
  and a non-empty target. Prompted by a real run on a second account that sat for 15 minutes
  with an empty folder while the session tarred and checksummed things — it had lost the
  plugin scripts and was improvising.
- **Bootstrap Step 1.5 forbids improvising.** If the plugin locator finds nothing, stop and
  say so: no `find`, no `ls -R`, and never a sweep of `/sessions/*/mnt/`, which can force a
  cloud provider to materialise thousands of files — looks like a hang, may quietly download
  gigabytes, and will not find the plugin anyway. States the benchmark plainly: a correct
  scaffold is ~0.03s and ~31 files, so minutes means stuck, not slow.
- **Language switches mid-conversation are handled.** People often open in English and drop
  into their own language once the interview gets personal. Same signal, arriving late.
- **Corrected a documented finding.** HANDOFF claimed the raw `~/Library/CloudStorage/…`
  Google Drive path would not mount and needed a `~/gDrive` symlink. It does mount, and a
  canary round-trips fine; Cowork's folder picker canonicalises symlinks anyway, so the
  workaround does not survive. "Available offline" is still genuinely required.

