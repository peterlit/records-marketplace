# Handoff — read this first

*Written 2026-09-02 at the end of a long Cowork session, for whoever (or whatever) picks this up next — most likely a fresh Claude Code session with no memory of how any of it was decided.*

## What this is

A Claude plugin that bootstraps and runs a **structured personal records project** — a medical case, a legal matter, anything that accumulates documents, advisors and decisions over time. It generates an Obsidian-friendly markdown vault plus a `CLAUDE.md` "engine" that keeps the vault current on every subsequent chat.

It was extracted from a real, year-old medical records project. **The folder structure is the cheap part.** The valuable part is the operating knowledge encoded in the templates and skills — see "Hard-won rules" below.

## Current state

**v0.6.0.** Seven skills, six scripts, two domain presets, five provider profiles.
Solo and shared modes both work; verified against a real Google Drive folder.

Note for a Claude Code session: earlier handoffs warned that **git cannot commit through a
Cowork-mounted folder** (git appends to `.git/logs/HEAD`; the mount refuses appends to
existing files, "Resource deadlock avoided"). That is a Cowork limitation only — commit
normally here, and `sh hooks/install.sh` gives you working pre-commit/pre-push gates.

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
| **Google Drive: the raw `CloudStorage` path works** | ⚠️ **Corrected 2026-09-02.** An earlier finding here claimed the raw `~/Library/CloudStorage/GoogleDrive-<acct>/…` path *will not mount* and that a `~/gDrive` symlink was required. **That is not true in current Cowork** — the raw path mounts, and a canary write/read/delete round-trips correctly. Cowork's folder picker canonicalises symlinks anyway, so the workaround does not survive being re-added. Drive **"Available offline"** is still required: streaming mode yields empty reads and 0-byte writes. `preflight.py` now detects exactly that. |
| **The Drive connector CAN do a full CRUD loop** | ⚠️ **Corrected 2026-09-03, twice wrong before.** (a) `read_file_content` returns **empty** for `text/markdown` — it is not in its supported-types list. The right tool is **`download_file_content`**, which returns base64 and round-trips **byte-identical** (md5 verified: wikilinks, tables, em-dashes, backticks all survive). The earlier "reads are escaped" note came from reading a Google *Doc*, not a `.md`. (b) `update_file` is still metadata-only, but content edits work as **create-new → trash-old → rename**. So the earlier conclusion that *"a filesystem-less surface can comprehend and append, never curate"* is **false** — curation is possible, just chatty (≈3 calls per edit). |
| **Markdown survives on Drive** | With `disableConversionToGoogleType: true`, `.md` stays `text/markdown` rather than becoming a Google Doc. |
| **Frontmatter portability** | Outside Claude Code only `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` are legal. Any other key is a **hard error**, not a warning. `lint_frontmatter.py` enforces this. |
| **Google Drive auto-linkifies path-shaped text** | In Drive's `.md` plain-text preview, `[Conditions](Conditions/Conditions.md)` renders as a clickable, **broken** `http://conditions/Conditions.md`. Wikilinks are ugly there but **inert**, so nothing breaks. See "Decisions already taken" below — link-style options were built and deliberately reverted. |

## Decisions already taken — don't redo these

**Link style: wikilinks only.** `--links wiki|markdown|plain` was built (v0.5.0/0.5.1) and **reverted** (0.4.0 + `records-export-doc`). Markdown links are *worse* than wikilinks on Drive for the reason in the table above, and `plain` only looked marginally nicer while losing Obsidian navigation and Folder Notes click-through entirely. The maintainer judged the option not worth its complexity. **If the "markdown looks ugly in Drive" complaint comes back, the answer is `records-export-doc`** — render a formatted Google Doc on demand — not a link-style setting.

**`bootstrap-records-project` is explicit-invocation-only.** Decided 2026-09-02 by the
maintainer, who uses this plugin for a real medical project. Rationale: he bootstraps a project
perhaps twice a year, but has hundreds of unrelated chats — so the expected cost of a false
positive vastly exceeds the benefit of a natural-language trigger he doesn't need. Inside a
project, the generated `CLAUDE.md` runs the workflow, so nothing is lost. **Do not "improve"
this by widening the description again**; evals 1–3 were flipped from positives to negatives to
lock it in, and eval 25 is the case it must not fire on.

⚠️ Enforcement is the **description field only**. `disable-model-invocation: true` would be the
hard switch, but it is not one of the six portable frontmatter keys and is a hard error outside
Claude Code (`lint_frontmatter.py` will reject it). If that key ever becomes portable, set it
and delete the prose.

**No static triggering metric.** A word-overlap analyzer (`lint_triggering.py`) was built
and deleted the same day. It cannot see negation — adding "DO NOT USE for X" *raises* the
score against X — and after three tunings it ranked `records-sync-status` top for "my mother
was just diagnosed". **Do not rebuild it.** Keep `evals/evals.json` and run it through
skill-creator's `run_eval.py`, which puts Claude in the loop. Triggering has no cheap proxy.

**Google Docs as storage: no.** Verified by creating one: on the Drive mount a Doc is a ~170-byte `.gdoc` pointer, not content. `grep` can't search it, Obsidian can't read it, the connector can't edit it, and **`snapshot.py` would archive only pointers and report success** — backups containing no data. Docs are for *export*, never for storage.

## Hard-won rules the generated projects depend on

These exist because the source project got them wrong repeatedly. They are the actual payload.

1. **Check the settled register before "correcting" the record.** A value printed on a source document does **not** automatically outrank a curated record — sources contain clerical errors. Ask *"was this already adjudicated?"*, not *"what does the document say?"*
2. **Memory is a convenience, never a source of truth.** Anything that must stay true across chats goes in a file. If memory and a file disagree, the file wins. (This is also what makes multi-user viable — memory is per-account and diverges.)
3. **Event date, not upload date.** A lab drawn on the 17th and reported on the 29th files under the 17th.
4. **Flag conflicting values; never silently overwrite** a trend table.
5. **Verify writes are non-zero.** Cloud-only files copy as 0 bytes and fail silently.

## Failure mode to design against: the silent hang

A bootstrap that "runs for 15 minutes" is **always** stuck, never slow — a correct scaffold is
0.03s and 31 files. Observed 2026-09-02 on a second account: the folder stayed empty while the
session tarred and checksummed things (`/tmp/rp.tgz`), i.e. it had lost the plugin scripts and
was improvising. `scripts/preflight.py` exists to convert every such case into a two-second
failure with a specific message, and `bootstrap-records-project` Step 1.5 now forbids the
improvisations — no filesystem sweeps, and never across `/sessions/*/mnt/`, which can force a
cloud provider to materialise thousands of files.

## Prose is not a guard (2026-09-03)

Two data-loss bugs in one day, both with the same shape: a rule that existed only in SKILL.md
text. `--reconfigure` blanked the control panel; `scaffold.py` reset a live vault's Master
Summary, settled register and question lists to templates and exited 0. Both were "prevented"
by a sentence telling the model to be careful.

**If a rule protects data, put it in the script.** The model reads instructions and mostly
follows them; a script refuses every time, including when the model is tired, wrong, or
improvising around an unrelated failure. Every remaining prose-only safety rule in this plugin
should be read as an open bug.

## The `--reconfigure` lesson (2026-09-02)

`--reconfigure` shipped able to blank a real project's `CLAUDE.md` — subject replaced by a
placeholder, advisors gone. It had been "verified" by re-supplying every flag, which is the
one case that cannot fail. **When a function's contract is "preserve what I didn't mention",
the only meaningful test is the one that mentions nothing.** `_persisted()` is now the single
source of what a vault remembers; if a field renders into `CLAUDE.md` and is not in there, the
bug is back.

## What's next

- **Refresh the installed plugin and use it for real.** The Update button greys out because
  Cowork caches *marketplace* metadata; uninstall and reinstall forces a refresh. Everything
  below this line has been tested locally; almost nothing has been tested by a second person.
- **Run `evals/evals.json` through skill-creator's `run_eval.py`.** Triggering remains the
  least-verified property of the plugin, and there is no cheap substitute (see above).
- **A third preset** would test whether the core/preset seam is real. `generic` is currently
  a hypothesis, not a demonstration — it has never been used for an actual non-medical case.
- **Decide whether `records-spike` ships.** It is a diagnostic for the builder, not the user.
- **Dropbox profile is unverified.** `templates/providers/dropbox.json` was written from
  documentation; no Dropbox vault has been built.

## Where the reasoning lives

`docs/design/` — the plan, the shared-Drive design (with all empirical results inline), and the earlier multi-user addendum. They're written as running documents with findings appended, so later sections sometimes supersede earlier ones; the supersessions are marked.

*Personal identifiers were redacted from these before they entered this repo. If you add more design notes from a private vault, run `lint_privacy.py` over them first.*
