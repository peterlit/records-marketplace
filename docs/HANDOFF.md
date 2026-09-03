# Handoff — read this first

*Written 2026-09-02 at the end of a long Cowork session, for whoever (or whatever) picks this up next — most likely a fresh Claude Code session with no memory of how any of it was decided.*

## What this is

A Claude plugin that bootstraps and runs a **structured personal records project** — a medical case, a legal matter, anything that accumulates documents, advisors and decisions over time. It generates an Obsidian-friendly markdown vault plus a `CLAUDE.md` "engine" that keeps the vault current on every subsequent chat.

It was extracted from a real, year-old medical records project. **The folder structure is the cheap part.** The valuable part is the operating knowledge encoded in the templates and skills — see "Hard-won rules" below.

## Current state

- **v0.3.0, staged but NOT committed.** 9 files, ~132 insertions. See `git status`.
- Reason it wasn't committed: **git cannot commit through a Cowork-mounted folder** — git appends to `.git/logs/HEAD` on every commit, and the mount refuses appends to existing files ("Resource deadlock avoided"). Creating new files in `.git/` works; appending does not. **In Claude Code this is a non-issue** — commit normally.
- Commit message drafted; gates were run manually against exactly this content and passed.

```bash
git status                     # 9 staged files
sh hooks/install.sh            # installs pre-commit + pre-push (they work here)
git commit && git push
```

## Verify before trusting anything

```bash
P=plugins/records-project
python3 $P/scripts/lint_frontmatter.py                    # portable 6-key SKILL.md frontmatter
python3 $P/scripts/lint_privacy.py                        # no subject data may ship
python3 $P/scripts/scaffold.py /tmp/v --preset health --subject "Test" \
        --advisor "Dr. X:role" --obsidian
python3 $P/scripts/validate_vault.py /tmp/v               # must print "vault valid"
```

⚠️ **`.privacy-patterns` is gitignored and contains real names.** Copy `.privacy-patterns.example` and fill it in, or the gate fails closed (by design). It does **not** ship.

## Findings that were expensive to establish — do not re-derive these

| Finding | Detail |
|---|---|
| **Marketplace plugins mount at `.remote-plugins/<opaque-id>/`** | **Not** `.claude/skills/`, and the directory name is an opaque id, *not* the plugin name. Built-in plugins mount flat by skill name. The locator in `bootstrap-records-project/SKILL.md` handles all four cases — **it was wrong until a real install proved it.** |
| **`CLAUDE_PLUGIN_ROOT` does not exist in the Cowork sandbox** | Only `CLAUDE_TMPDIR` and proxy vars. It *is* set in Claude Code. **Never hardcode a plugin path in shell**; locate once, then let scripts self-resolve via `__file__`. |
| **Deletion protection is Cowork's, not the cloud provider's** | `rm` fails with "Operation not permitted" on iCloud, Google Drive, **and ordinary local disk**, and in `outputs`. This was misattributed to iCloud for months. Call **`allow_cowork_file_delete`**. |
| **Google Drive works, but needs a symlink** | The raw `~/Library/CloudStorage/GoogleDrive-<acct>/My Drive/…` path **will not mount** into the bash sandbox. A short symlink (`~/gDrive`) to the same place mounts fine. Also requires Drive for Desktop **"Available offline"** — streaming mode yields empty reads. |
| **The Drive *connector* cannot edit file contents** | `update_file` handles title and parentId only. And **reads are escaped** — `read_file_content` returns a "natural language representation" (`\# Heading`, `\[\[link\]\]`), not bytes. Storage is faithful; only the connector's read path mangles it. Consequence: **a filesystem-less surface (Slack) can comprehend and append, never curate.** |
| **Markdown survives on Drive** | With `disableConversionToGoogleType: true`, `.md` stays `text/markdown` rather than becoming a Google Doc. |
| **Frontmatter portability** | Outside Claude Code only `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` are legal. Any other key is a **hard error**, not a warning. `lint_frontmatter.py` enforces this. |
| **Google Drive auto-linkifies path-shaped text** | In Drive's `.md` plain-text preview, `[Conditions](Conditions/Conditions.md)` renders as a clickable, **broken** `http://conditions/Conditions.md`. Wikilinks are ugly there but **inert**, so nothing breaks. See "Decisions already taken" below — link-style options were built and deliberately reverted. |

## Decisions already taken — don't redo these

**Link style: wikilinks only.** `--links wiki|markdown|plain` was built (v0.5.0/0.5.1) and **reverted** (0.4.0 + `records-export-doc`). Markdown links are *worse* than wikilinks on Drive for the reason in the table above, and `plain` only looked marginally nicer while losing Obsidian navigation and Folder Notes click-through entirely. The maintainer judged the option not worth its complexity. **If the "markdown looks ugly in Drive" complaint comes back, the answer is `records-export-doc`** — render a formatted Google Doc on demand — not a link-style setting.

**Google Docs as storage: no.** Verified by creating one: on the Drive mount a Doc is a ~170-byte `.gdoc` pointer, not content. `grep` can't search it, Obsidian can't read it, the connector can't edit it, and **`snapshot.py` would archive only pointers and report success** — backups containing no data. Docs are for *export*, never for storage.

## Hard-won rules the generated projects depend on

These exist because the source project got them wrong repeatedly. They are the actual payload.

1. **Check the settled register before "correcting" the record.** A value printed on a source document does **not** automatically outrank a curated record — sources contain clerical errors. Ask *"was this already adjudicated?"*, not *"what does the document say?"*
2. **Memory is a convenience, never a source of truth.** Anything that must stay true across chats goes in a file. If memory and a file disagree, the file wins. (This is also what makes multi-user viable — memory is per-account and diverges.)
3. **Event date, not upload date.** A lab drawn on the 17th and reported on the 29th files under the 17th.
4. **Flag conflicting values; never silently overwrite** a trend table.
5. **Verify writes are non-zero.** Cloud-only files copy as 0 bytes and fail silently.

## What's next

- **S2/S3 of the shared-Drive design** — in-folder `MEMORY.md`, `_sync` presence markers, optimistic concurrency on curated files. See `docs/design/02-shared-drive-design.md`.
- **Provider profiles as data** (`templates/providers/*.json`) + **`.records-project.json`** so a vault describes itself + **`scaffold.py --reconfigure`**. Makes the storage provider reversible. §1f of the same doc.
- **Triggering evals.** The least-tested part of the whole plugin. Descriptions were checked for keyword coverage, which is *not* the same as checking behaviour. Use `skill-creator`'s eval harness.
- **A third preset** would test whether the core/preset seam is real. `generic` is currently a hypothesis, not a demonstration.
- Decide whether `records-spike` (a diagnostic) should ship to end users at all.

## Where the reasoning lives

`docs/design/` — the plan, the shared-Drive design (with all empirical results inline), and the earlier multi-user addendum. They're written as running documents with findings appended, so later sections sometimes supersede earlier ones; the supersessions are marked.

*Personal identifiers were redacted from these before they entered this repo. If you add more design notes from a private vault, run `lint_privacy.py` over them first.*
