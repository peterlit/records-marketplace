# Modes, conversions, and what has actually been tested

*Written 2026-09-04. The last section is the honest part — most combinations have never been
run by a real person, and the gap between "validates" and "works" is where every bug this
project has found came from.*

## The dimensions

Six settings change **structure** (which files exist, what the engine says to do):

| Dimension | Values | Effect |
|---|---|---|
| **preset** | `health`, `generic` | Folder names (`Results/Visits` vs `Records/Meetings`) and all vocabulary (*doctor* vs *advisor*) |
| **provider** | `gdrive`, `dropbox`, `icloud`, `onedrive`, `local` | Sync hazards in `CLAUDE.md`, conflict patterns for the validator, onboarding text in START HERE |
| **mode** | solo, shared (≥2 co-users) | `_sync/` markers, co-user framing, re-read-before-write rule, in-folder memory |
| **language** | English, anything else | `## Language` section pinning every future session; prose translated, structure stays English |
| **obsidian** | on, off | `.obsidian/` config and Folder Notes |
| **snapshot** | `master`, `always`, `never` | When a zip is taken |

Four change **content only** — wording and framing, no files: `conservatism`
(`conservative`/`balanced`/`interventionist`), `decision_maker`, `memory`, `store_sensitive`.

One co-user is **not** shared mode. Shared needs two or more; a single `--co-user` silently
stays solo, which is the easiest mistake to make when phrasing a bootstrap request.

## Conversions

`--reconfigure` re-renders `CLAUDE.md` and the config. **It never touches curated content** —
verified byte-for-byte in the suite.

| From → To | How | Notes |
|---|---|---|
| solo → shared | `--reconfigure --co-user A --co-user B` | Creates `_sync/` and its folder note. Common case: a project becomes shared later. |
| shared → solo | `--reconfigure --solo` | `_sync/` markers are left on disk as history; only the mode changes. |
| provider → provider | `--reconfigure --provider X` | Swaps hazards, conflict patterns, onboarding. Move the files yourself. |
| language → language | `--reconfigure --language X` | Pins future sessions. **Existing prose is not translated** — that is a bootstrap-time step. |
| obsidian on → off | `--reconfigure --no-obsidian` | |
| obsidian off → on | `--reconfigure --obsidian` | |
| conservatism / decision-maker / snapshot / consent | `--reconfigure --<flag> X` | Content-only. |
| **preset → preset** | **not supported** | Refused in code. The folder names differ, so a re-render leaves engine and folders disagreeing and the validator cannot see it. Build a new vault and move content deliberately. |
| older version → current | `migrate.py --apply` | Reports first. Requires any setting the old config never stored. |
| hand-built → adopted | `migrate.py --adopt --apply` | ⚠️ Re-renders `CLAUDE.md`, discarding hand-edits. Read them out first. |

**Omitting a flag means KEEP.** That is why `--solo` and `--no-obsidian` exist: without an
explicit off-switch a vault can only ever gain settings, never lose them. Any new boolean
needs the same treatment.

## What has actually been exercised

"Validated" means the suite builds it and `validate_vault.py` passes. **"Real use" means a
person used it for real work over time** — the only thing that has ever found a serious bug here.

| Combination | Status |
|---|---|
| health · icloud · solo · English · obsidian | **Real use, ~1 year** — but hand-built, predating the plugin. Its `CLAUDE.md` is the source all of this was extracted from. |
| health · gdrive · solo · English · obsidian | **Real bootstrap, once**, on a second account. Produced 4 real bugs including 2 data-loss. |
| health · gdrive/icloud/local · solo/shared | Validated in the suite, all 5 providers × both modes |
| generic · any | Validated only. **Never used for a real non-medical case.** |
| any · shared, two real people | **Never.** Zero two-person runs on two machines. |
| non-English | Validated only. Never a real project. |
| dropbox, onedrive | Validated only. Both profiles written from documentation; no vault has ever lived on either. |
| preset switching | Refused by design. |

## Most in need of real testing, in order

1. **Shared mode with two actual people on two machines.** It has produced bugs on every
   inspection so far — the interview never asked for co-users, `{{#if SHARED}}` dropped the
   sync-status row, the reconfigure retrofit left an invalid vault, and shared→solo was a
   one-way door. All four were found by reading, not running. Nothing has ever tested two
   Claude accounts writing to one folder, which is the entire point of the mode. The specific
   unknowns: whether presence markers propagate usefully before they go stale, whether
   re-read-before-write actually prevents a fork under real sync latency, and whether the
   Prompt Log is enough for each person to learn what the other did.
2. **`generic` for a real non-medical case.** The core/preset seam is a hypothesis. The suite
   proves the vocabulary differs; it cannot prove the *structure* fits a legal matter or a
   tax history. A second real domain is the only way to find out whether `01 Master` and the
   settled register generalise or are quietly medical in shape.
3. **A non-English project.** Bootstrap Step 2b translates seeded prose, and nothing has ever
   checked what that produces. Structure-in-English with translated prose is a design guess.
4. **iCloud eviction under real conditions.** `preflight.py` detects `.icloud` stubs, but the
   dangerous case — a co-user with Optimise Mac Storage on, mid-session — has only ever been
   simulated with `touch`.
5. **Dropbox and OneDrive**, written from docs and never run.

## What this says about the regression suite

The suite is good at **the things it can see**: 68 tests, every one tied to a shipped bug,
mutation-checked. It covers all 5 providers × 2 modes, every conversion, and every gate in both
directions.

It cannot see the four things that actually matter most, and no unit test can:

- **Two writers on one synced folder.** Sync latency, conflict copies, and stale markers are
  properties of a real cloud provider and two real machines. A test can create a file named
  `Master Summary 2.md`; it cannot make Dropbox create one.
- **Whether the *content* is any good.** Nothing checks that a critique is balanced, that a gap
  audit finds real gaps, or that the settled register stops the re-opening it exists to stop.
  That is what `evals/evals.json` is for, and it has still never been run.
- **Triggering.** Whether a skill fires when it should and stays silent when it should not is a
  model behaviour. A static analyser was built for this and deleted the same day; it cannot see
  negation.
- **Whether the structure fits a domain.** Only a real case answers that.

So the honest reading: the suite protects against *regression* well and says nothing about
*fitness*. Both real-use bootstraps so far produced multiple bugs the suite would never have
caught, because they were bugs of the form "this does not survive contact with a real person".
The next most valuable thing is not more tests — it is **one shared, two-person project run for
a month**, and **one `generic` project for a real non-medical case**.
