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

## 0.7.1 — 2026-09-02

Everything here came out of one real bootstrap run on a second account, by a Claude that
reported four findings at the end. All four were real.

- **FIX (data loss): `--reconfigure` silently blanked the control panel.** It promised to
  "carry forward everything the caller did not explicitly override" but carried forward only
  preset, co-users and Obsidian. `--reconfigure --provider dropbox` on a real vault
  re-rendered `CLAUDE.md` with subject "the subject", no advisors, no decision-maker and
  conservatism reset — **the subject's name simply disappeared.** Cause was structural: `ctx`
  was built from the parsed args before the reconfigure block ran, so restoration was a few
  piecemeal patches instead of the default. Restoration now happens immediately after
  `parse_args`, driven by which flags actually appear in `sys.argv`, and `_persisted()` is now
  the single definition of what a vault remembers about itself — every field used to render
  `CLAUDE.md` is stored. A bare `--reconfigure` is now a verified byte-for-byte no-op across
  all 31 files. *An earlier "verified: touches no content" check passed because it re-supplied
  every flag — the one case that cannot fail.*
- **FIX: the locator missed cloud-linked sessions entirely.** There the plugin lives in the
  cloud container (`~/.claude/plugins/synced/<id>/`) while the target folder is reachable only
  from the device VM. None of the four strategies fired on either side. Added a fifth.
- **CORRECTS 0.7.0's "never copy the plugin" rule, which was wrong.** It conflated two
  different things and would have blocked the workaround that made the run succeed. Sweeping
  the filesystem to *find* the plugin stays forbidden; copying `scripts/` and `templates/`
  into scratch to bridge two execution contexts is legitimate and now documented — including
  packing `.claude-plugin/` so the version is not lost.
- **`--plugin-version`** for bridged runs, which otherwise stamp `plugin_version: unknown`.
- **A leftover `.preflight-canary` is now a validation failure.** Under Cowork's deletion
  protection preflight cannot remove its own canary; it warns and exits 0, which is correct,
  but the file stayed behind. Better to fail loudly than leave litter in someone's vault.

## 0.8.0 — 2026-09-03

- **FIX (data loss, worst yet): `scaffold.py` would silently overwrite a live vault.**
  Re-running it on an existing project reset the Master Summary, the settled register, every
  question list and the Timeline to empty templates — no warning, exit 0, success message.
  A year of curation, gone from one command. **The only guard was a sentence in SKILL.md.**
  It now refuses in code when the target contains `.records-project.json`, `CLAUDE.md` or
  `01 Master/`, pointing at `--reconfigure`; `--force` still allows deliberate teardown, and
  scaffolding *alongside* unrelated pre-existing files warns but proceeds and preserves them.
  Second prose-only guard to fail in one day, after `--reconfigure`. **If a rule protects
  data, it belongs in the script, not the instructions.**
- **FIX: cloud-linked locator was one level short.** The real layout nests the plugin name
  under the sync id — `~/.claude/plugins/synced/<sync-id>/<plugin>/skills/<skill>` — so the
  0.7.1 glob printed NOT FOUND. All four depths now tried.
- **NEW `records-chat-companion`.** Generates paste-ready claude.ai Project instructions so an
  existing Drive-hosted vault can be consulted away from the computer. Reads
  `.records-project.json`, so subject, decision-maker, conservatism and language match the
  authoritative side. The companion reads everything and writes **only** into `03 Inbox/`,
  marked *not yet filed*, for `file-to-records` to pick up. That restriction is policy, not a
  technical limit: the connector can curate (create-new → trash-old → rename, byte-fidelity
  verified), but the chat surface has no preflight, no validator, no snapshot and no 0-byte
  detection, and cannot see what Cowork is doing.
- **Connector facts corrected, twice wrong before.** `read_file_content` returns an **empty
  string** for `text/markdown` — not an error — so a companion using it concludes the record
  is blank. `download_file_content` round-trips byte-identically (md5 verified). The earlier
  conclusion that a filesystem-less surface "can comprehend and append, never curate" was false.

## 0.8.1 — 2026-09-03

Three bugs found in scratch testing, all in shared mode — which had never been exercised
end-to-end from the interview onward.

- **FIX (systemic): `{{#if}}` failed silently while `{{VAR}}` failed loudly.** `{{VAR}}` raised
  `KeyError` on an unknown key, but `{{#if X}}` used `ctx.get()`, so a mistyped condition
  deleted its block instead of erroring. That is how `{{#if SHARED}}` (context key is lowercase
  `shared`) dropped the `records-sync-status` row from **every** shared project's skills table —
  the one row telling co-users how to check whether the other is working. Both forms now raise.
  The typo was the symptom; the asymmetry was the bug.
- **FIX: the interview never asked about co-users.** Steps 1–13 covered operator,
  decision-maker, advisors and consent, but nothing prompted for co-users, so a model following
  the skill would only ever build a solo project unless the user volunteered the idea — making
  shared mode effectively unreachable through its own front door. Now asked directly, with the
  peer-not-helper distinction and a warning that one `--co-user` silently stays solo.
- **FIX: `--reconfigure` into shared mode produced an invalid vault.** It created `_sync/` with
  `os.makedirs` but skipped the template walk that writes `_sync/_sync.md`, so
  `validate_vault.py` failed immediately with `missing folder note`. Fresh shared scaffolds were
  fine; only the retrofit path was broken — the path someone uses when a project becomes shared
  later, which is the common case.

## 0.9.0 — 2026-09-04

Shared-mode hardening, after establishing how Cowork actually reaches a local folder from
a phone. Two of these correct guidance that was wrong rather than merely missing.

- **NEW: preflight proves reads, not just writes.** The canary only ever demonstrated that a
  *new* file could be written — it said nothing about the files already there. On a synced
  vault an evicted file **reads as 0 bytes rather than erroring**, and the danger is not a
  failed read but a successful-looking empty one that gets summarised and written back,
  destroying the file for every co-user. `preflight.py` now refuses on any existing vault
  containing eviction stubs, zero-byte markdown, or a `CLAUDE.md`/Master Summary that reads
  empty. **The re-read-before-write rule assumed reads were honest; on a cloud mount they are
  not.**
- **FIX: eviction was reported as a sync conflict.** Both surfaced as `SYNC CONFLICT COPY`,
  sending people to look for a merge that does not exist. They are now distinct: forks say
  *"the record has forked"*, evictions say *"turn OFF Optimise Mac Storage"*. Old vaults with
  the pattern baked into their config are handled too.
- **CORRECTS the iCloud sharing guidance.** The profile said *"awkward for multi-user work;
  prefer Dropbox or Drive"* — reasoning from the absence of a connector. **Cowork does not need
  a connector; it reads the local filesystem.** iCloud folder sharing with "Can make changes"
  is a first-class option for co-users. The real requirement is that **"Optimise Mac Storage"
  is off on BOTH machines**, since eviction is per-machine and one co-user's setting can empty
  files the other depends on.
- **NEW: the shared block explains working from a phone.** Cowork on mobile/web reaches a
  connected folder only while the desktop app is open on that machine *and* the session was
  started on desktop — a project tied to a local folder cannot start a Cowork session from
  mobile. Start on the computer, resume from the phone; `Dispatch → Get started` has the
  keep-awake toggle. Written down because "Claude can't see the folder from my phone" looks
  exactly like a sync failure and isn't one.

## 0.9.1 — 2026-09-04

- **NEW: a regression suite — 40 tests, ~1.5s, stdlib only.**
  `plugins/records-project/tests/test_regressions.py`. **Every test corresponds to a bug that
  actually shipped**, and each carries a docstring saying what went wrong, so a future failure
  is legible without archaeology. Wired into `hooks/pre-push`.

  Covered: scaffolding over a live vault (and that the refusal touches zero bytes); bare
  `--reconfigure` as a byte-level no-op; one-field reconfigure preserving subject, advisors,
  decision-maker, conservatism and language; every rendered field being persisted;
  `{{#if}}`/`{{VAR}}` both raising on unknown keys, plus a sweep asserting no template
  condition is upper-case; validator rejecting a nonexistent folder, 0-byte files, language
  drift and a leftover canary; eviction and forks producing *different* messages; the OneDrive
  false positive on the settled register; preflight refusing an evicted or 0-byte vault;
  one co-user staying solo while two enable shared; the `_sync` folder note on the reconfigure
  retrofit; the started/stopped tie-break at equal timestamps; the chat companion refusing a
  non-project and naming `download_file_content`; and every script importing stdlib only.

  **Mutation-checked**: reverting the overwrite guard makes the suite fail, so it is testing
  behaviour rather than asserting tautologies.

  The suite's first run failed — on itself. `lint_privacy.py` caught a real clinical value used
  as a test fixture. **A fixture is as public as any other line of code**, and the packaging
  test now scans the tests too.

## 0.10.0 — 2026-09-04

- **`00 START HERE.md` now onboards a second person**, not just describes the folder. It
  previously assumed whoever opened it had already set everything up — true for the person who
  ran bootstrap, false for every co-user after them, and false again for the first person on a
  new machine.

  Four steps, in the order that matters: (1) make the folder **available offline**, rendered
  from the provider profile so each storage backend gets its own wording — *"Available offline"*
  for Drive, *"Turn OFF Optimise Mac Storage"* for iCloud, *"Always keep on this device"* for
  OneDrive, out of *Smart Sync* for Dropbox, and nothing at all for a local folder; (2) point
  Cowork at the folder with **Add Folder**; (3) run **preflight** to confirm reads are
  trustworthy; (4) type **`orient`** as a first prompt, with the failure signal spelled out —
  *if Claude asks you to explain the history instead, stop.*

  Step 1 leads because skipping it does not produce an error. A cloud-placeholder file **reads
  as empty and succeeds**, so Claude sees a blank Master Summary and writes a "corrected"
  version over it. In shared mode the note adds that the setting is per-machine, so one
  co-user's choice determines what the other loses.
- **Shared vaults get a co-user orientation**: read the Prompt Log first because your account
  cannot see the other person's chats; your Claude memory is private and will drift; and Cowork
  on mobile reaches the folder only while your desktop app is open, for a session started on
  desktop — which looks like a sync failure and isn't.
- **Five onboarding tests** covering provider-specific wording, local getting no cloud ceremony,
  the presence of the Cowork step / preflight step / first prompt, and co-user guidance
  appearing only in shared mode.

## 0.11.0 — 2026-09-04

- **NEW `records-migrate` + `migrate.py`** — bring an older or hand-built vault up to the
  current version. **Reports by default and writes nothing**; `--apply` snapshots first, then
  re-renders only generated files. Afterwards it compares mtime and size of every file under
  `01 Master`–`99 Archive` and **aborts if a single curated file changed**.
  `--adopt` writes a `.records-project.json` for folders that predate self-description, so
  `--reconfigure`, the validator and the other skills stop refusing.
- **Caught in development, and it was today's bug wearing a new hat:** `--apply` on a vault
  whose old config lacked `subject` re-rendered `CLAUDE.md` with the placeholder *"the subject"*
  over the person's name — while printing *"vault valid"* and *"migrated to 0.10.0"*. The
  curated-content check passed, because `CLAUDE.md` is generated and so not in the sacred list.
  **The finding said the value was unknown, and the code applied anyway.** Now: a missing
  setting means UNKNOWN, not empty; `--apply` refuses while any required setting is unknown and
  names the flags it needs; and a post-render guard fails if any placeholder reached
  `CLAUDE.md`. The skill tells the model to *recover* the values from the old `CLAUDE.md` and
  question lists, and to ask rather than invent.
- The skill also warns, before adopting, that re-rendering **discards hand-edits to
  `CLAUDE.md`** — for a long-running project those local rules are often the most valuable
  thing in the folder, so read them out and offer to carry them across.
- **Eight migration tests**, including that report mode writes nothing, that applying with
  unknowns refuses *and leaves the name intact*, and that curated content is byte-identical
  after a successful migration. Suite is now 52 tests.

