---
name: bootstrap-records-project
description: Set up a structured personal records project - medical case, legal matter, or any ongoing situation with documents, advisors and decisions to track. Creates an Obsidian-friendly vault with a Master Summary, chronological chronicle, per-advisor question lists, a settled-questions register, and a filing workflow that runs automatically thereafter. Use this whenever someone wants to organize, track, get on top of, or start keeping records for a medical diagnosis, a health situation, a legal matter, an elderly parent's care, or any body of documents that accumulates over time - even if they never say the words "project" or "records". Also use when someone is overwhelmed by paperwork, test results, or correspondence and wants a system for it.
license: MIT
---

# Bootstrap a records project

Creates a working vault plus the standing workflow that keeps it current. The person's only ongoing job afterwards is dropping files into `03 Inbox`.

## Before you start

**Do not scaffold into a folder that already has content** unless the person confirms. Check first.

If a `CLAUDE.md` and `01 Master/` already exist, this project is already set up — don't re-bootstrap it. Read the existing `CLAUDE.md` and follow it instead.

## Step 1 — interview

Ask these as **one or two batched multiple-choice rounds**, not an interrogation. Infer what you reasonably can from what they've already said and confirm rather than asking cold. If they've described a cancer diagnosis, don't ask which domain.

**Essential — you cannot build without these:**

1. **Domain** → `--preset health` or `--preset generic`.
2. **Whose records** (the subject's name) → `--subject`. Optionally date of birth → `--dob`.
3. **Where to build it** — the target folder.

**Important — ask, but offer a sensible default:**

4. **Who decides?** Name the decision-maker → `--decision-maker`. ⚠️ **Do not assume it is the person typing.** A daughter managing her father's care is not the decision-maker; he is. This changes how Claude frames every recommendation thereafter, so it is worth one direct question.
5. **Who operates the project?** (whoever is doing the filing) → `--operator`.
6. **The advisors** — names and roles → repeated `--advisor "Name:role"`. Each gets a question list, pre-split Urgent / Next / Settled.
7. **Conservatism dial** → `--conservatism conservative|balanced|interventionist`. Frame it plainly: *"When there's a choice between watchful waiting and an invasive procedure, how do you want options presented?"* Default `balanced`. This is the decision-maker's call, not the operator's.
8. **One-line situation summary** → `--situation`, seeds the Master Summary.

**Ask only if not obvious:**

9. **Obsidian?** → `--obsidian`. Default **on** if they use it or don't know; harmless if unused. It installs the Folder Notes plugin config and writes a folder note per folder.
10. **Storage provider** → `--provider gdrive|dropbox|icloud|onedrive|local`. **Infer it from the target path and confirm** rather than asking blind. This loads a provider profile that decides three things: the sync hazards written into the generated `CLAUDE.md`, the mount and offline-mode setup notes, and the **conflict-copy patterns the validator will use**. ⚠️ For `gdrive`, the profile carries the symlink requirement — the raw `CloudStorage` path will not mount into the sandbox.
11. **Snapshot trigger** → `--snapshot master|always|never`. Default `master` (only when `01 Master/` changes) — this is the setting that stops snapshot spam.

**Ask explicitly, never assume — these two are consent questions:**

12. **May Claude store this in memory across chats?** → `--memory`. **Only pass this flag on an explicit yes.** Without it the generated `CLAUDE.md` tells Claude to skip memory updates. Say what it means: faster context in future chats, at the cost of the information persisting outside the folder.
13. **Sensitive personal data?** → `--store-sensitive`. For health projects, ask directly whether they consent to health details being stored in the project. Records the consent date in `CLAUDE.md`.

## Step 2 — build

Locate the scripts. **Never hardcode a plugin path in a shell command** — `${CLAUDE_PLUGIN_ROOT}` does not exist in every environment. Try in order, stop at the first hit:

```bash
# Resolve the plugin root. Order matters; stop at the first hit.
SKILL=bootstrap-records-project
ROOT=""
# 1. Claude Code sets this.
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT/scripts" ] && ROOT="$CLAUDE_PLUGIN_ROOT"
# 2. Cowork, marketplace-installed: .remote-plugins/<opaque-id>/ - the id is NOT the plugin name,
#    so identify our plugin by one of its skills, then step up two levels to the plugin root.
[ -z "$ROOT" ] && for d in /sessions/*/mnt/.remote-plugins/*/skills/$SKILL; do
  [ -d "$d" ] && ROOT="$(cd "$d/../.." && pwd)" && break
done
# 3. Cowork, built-in plugin: skills mount flat by skill name.
[ -z "$ROOT" ] && for d in /sessions/*/mnt/.claude/skills/$SKILL; do
  [ -d "$d" ] && ROOT="$(cd "$d/.." && pwd)" && break
done
# 4. Local dev.
[ -z "$ROOT" ] && for d in "$HOME"/.claude/skills/*/skills/$SKILL; do
  [ -d "$d" ] && ROOT="$(cd "$d/../.." && pwd)" && break
done
echo "plugin root: ${ROOT:-NOT FOUND}"
```

**Verified 2026-09-02 against a real marketplace install:** strategy 2 is the one that fires in Cowork. The plugin mounts read-only at `/sessions/<session>/mnt/.remote-plugins/<opaque-id>/` with `scripts/`, `skills/` and `templates/` all present, and the scripts execute normally. **Do not expect the plugin name in that path** — the directory is an opaque id.

Then run it, quoting every value:

```bash
python3 <scripts>/scaffold.py "<target>" \
  --preset health --subject "Jane Doe" --dob 1968-03-14 \
  --operator "Maria" --decision-maker "Jane Doe" \
  --advisor "Dr. Chen:cardiologist" --advisor "Dr. Okafor:PCP" \
  --conservatism conservative --snapshot master --provider dropbox --obsidian \
  --situation "Newly diagnosed atrial fibrillation; anticoagulation decision pending."
```

## Changing the provider later

A vault records its own settings in `.records-project.json`. If it moves to different storage, **do not re-scaffold** — reconfigure:

```bash
python3 <scripts>/scaffold.py "<vault>" --reconfigure --provider dropbox
```

That rewrites only `CLAUDE.md` and `.records-project.json`; **no content is touched** — no folder notes, no Master files, no chronicle. Preset, co-users and Obsidian setting carry forward unless overridden. It refuses to run without an existing `.records-project.json`, so it can never be mistaken for a fresh scaffold over live data.

## Step 3 — verify, always

```bash
python3 <scripts>/validate_vault.py "<target>"
```

It must print `vault valid`. It checks that every folder has a correctly-named folder note, every wikilink resolves, no file is 0 bytes, and no cloud-sync conflict copies are present. **If it fails, fix the cause before telling the person it's done.**

## Step 4 — seed and hand over

- If (and only if) they said yes to memory, write a short project memory: subject, domain, decision-maker, advisors, where the folder is.
- Tell them: **their only job is dropping things into `03 Inbox`**; everything else is automatic.
- Point them at `00 START HERE.md`, and mention that `CLAUDE.md` is the control panel they can edit.
- If Obsidian was enabled: they open the folder via Obsidian → "Open folder as vault", then approve community plugins on first launch.

## What gets built

```
00 START HERE.md · CLAUDE.md          the workflow engine
01 Master/       Master Summary · Settled — do not re-open · Questions — <each advisor>
02 Chronicle/    Timeline · Prompt Log  (+ Results/ Visits/ for health)
03 Inbox/        the only folder they file into
04 Critiques/    05 Trends/  (seeded CSVs)  06 Reference/ (+ Raw Archive/, Snapshots/)
07 Deep Dives/   99 Archive/
```

## Two rules the generated project depends on

Both exist because they were learned the hard way, and both belong in anything built from this:

1. **Check the Settled register before "correcting" the record.** A value printed on a source document does not automatically outrank a curated record — sources contain clerical errors. The question is *"was this already adjudicated?"*, not *"what does the document say?"*
2. **Memory is a convenience, never a source of truth.** Anything that must stay true across chats goes in a file. If memory and a file disagree, the file wins.
