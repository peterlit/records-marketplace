---
name: bootstrap-records-project
description: Scaffold a new structured records project - a vault with a Master Summary, chronological chronicle, per-advisor question lists, a settled-questions register, and a CLAUDE.md workflow engine that runs the project thereafter. ONLY use this skill when the user explicitly invokes it by name, or explicitly asks to bootstrap, scaffold or set up a records project. NEVER select it on your own initiative. Do not fire on someone describing a diagnosis, a legal matter, an ill relative, a pile of paperwork, or any request to organise, track or get on top of something - answer those normally and do not mention this skill. Inside an existing records project the CLAUDE.md in that folder already runs the workflow; this skill is only for creating a project that does not exist yet.
license: MIT
---

# Bootstrap a records project

Creates a working vault plus the standing workflow that keeps it current. The person's only ongoing job afterwards is dropping files into `03 Inbox`.

## This skill is invoked deliberately, never inferred

The description tells the model not to select this on its own. So if you are reading this,
**the person asked for it by name.** That has two consequences:

- **Do not re-litigate whether their situation qualifies.** They have already decided. Build
  what they asked for. Tax documents, a house renovation, an immigration case, a pet's chronic
  illness — all fine. Do not lecture them about what a records project is "for".
- **Do not ask questions they have already answered.** They usually name the domain, and often
  the subject and an advisor, in the same breath as invoking the skill. Take those and skip
  ahead.

One thing is still worth a single line when the fit is unclear: **does this keep accumulating,
or does it finish?** A one-off pile of receipts gets no value from a Settled register or a
question list. Say that in one sentence, offer a plain folder structure as the alternative, and
build whichever they pick — do not refuse.

If there are no advisors, the per-advisor question lists sit empty. That is fine; never invent
advisors to fill them.

## Before you start

**`scaffold.py` now refuses in code** if the target already contains `.records-project.json`,
`CLAUDE.md` or `01 Master/`, and tells you to use `--reconfigure`. Do not reach for `--force` to
get past it: that overwrites the Master Summary, the settled register and every question list
with empty templates. It exists for deliberate teardown, not for getting unstuck.

If a `CLAUDE.md` and `01 Master/` already exist, this project is already set up — don't re-bootstrap it. Read the existing `CLAUDE.md` and follow it instead.

## Step 0 — language, before anything else

**If the person is writing to you in a language other than English, do not silently continue in
English and do not silently continue in theirs.** Ask once, in *their* language, as the very
first thing:

> Should this project be kept in <their language>, or in English?

Then pass `--language "<answer>"`. It is written into `.records-project.json` and into the
generated `CLAUDE.md`, so **every future chat keeps writing in that language** — which is the
whole point. Getting it from the conversation alone is not enough; a later session starts with
no memory of how this one went.

Conduct the rest of the interview in whichever language they chose.

**Watch for a switch mid-conversation.** People often open in English and drop into their own
language a few turns later, once the interview gets personal. That is the same signal arriving
late, not a different one — ask the same question at that point rather than carrying on in
English. This applies after bootstrap too: if someone starts writing to an established project
in a new language, offer to change `--language` via `--reconfigure` rather than quietly
producing a bilingual record.

Two things to say plainly if they pick a non-English language:

- Folder and file names stay English (`01 Master`, `03 Inbox`) because the scripts and skills
  match on those exact strings. Their language goes in the folder note headings and all prose.
- Source documents are read in whatever language they are written; only the record is
  translated.

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
6b. **Will anyone else work in this project?** → repeated `--co-user "Name"`. **Ask this; do not
   wait to be told.** Two or more co-users switches the engine into shared mode: presence
   markers in `_sync/`, the re-read-before-write rule, and memory kept in the folder rather than
   in either account. Retrofitting later works (`--reconfigure --co-user A --co-user B`) but the
   framing of every generated file changes, so it is much better to know now.
   ⚠️ **A co-user is a peer, not a helper** — someone who both contributes *and* interrogates
   the record. A spouse managing care together is a co-user; a relative you occasionally forward
   a PDF to is not. Do not pass `--co-user` for one person: shared mode needs two or more, and
   one name silently stays solo.
7. **Conservatism dial** → `--conservatism conservative|balanced|interventionist`. Frame it plainly: *"When there's a choice between watchful waiting and an invasive procedure, how do you want options presented?"* Default `balanced`. This is the decision-maker's call, not the operator's.
8. **One-line situation summary** → `--situation`, seeds the Master Summary.

**Ask only if not obvious:**

9. **Obsidian?** → `--obsidian`. Default **on** if they use it or don't know; harmless if unused. It installs the Folder Notes plugin config and writes a folder note per folder.
10. **Storage provider** → `--provider gdrive|dropbox|icloud|onedrive|local`. **Infer it from the target path and confirm** rather than asking blind. This loads a provider profile that decides three things: the sync hazards written into the generated `CLAUDE.md`, the mount and offline-mode setup notes, and the **conflict-copy patterns the validator will use**. ⚠️ For `gdrive`, the profile carries the symlink requirement — the raw `CloudStorage` path will not mount into the sandbox.
11. **Snapshot trigger** → `--snapshot master|always|never`. Default `master` (only when `01 Master/` changes) — this is the setting that stops snapshot spam.

**Ask explicitly, never assume — these two are consent questions:**

12. **May Claude store this in memory across chats?** → `--memory`. **Only pass this flag on an explicit yes.** Without it the generated `CLAUDE.md` tells Claude to skip memory updates. Say what it means: faster context in future chats, at the cost of the information persisting outside the folder.
13. **Sensitive personal data?** → `--store-sensitive`. For health projects, ask directly whether they consent to health details being stored in the project. Records the consent date in `CLAUDE.md`.

## Step 1.5 — preflight, and NEVER improvise a search

```bash
python3 <scripts>/preflight.py "<target>"
```

It writes a canary, reads it back, checks the size is non-zero, and deletes it. **Under Cowork's
file-deletion protection the delete will fail** — that is expected, preflight warns and still
exits 0. Remove `.preflight-canary` with `allow_cowork_file_delete` before handing over; the
validator now fails if you forget. Every one of
those checks corresponds to a real failure that otherwise shows up as *a command that runs for
fifteen minutes and produces an empty folder*. **A correct scaffold takes about 0.03 seconds and
writes ~31 files.** Nothing on the happy path takes minutes. If something is taking minutes it
is stuck, not slow — stop and report, do not wait.

**If the plugin locator in Step 2 finds nothing, STOP and say so.** Do not fall back to `find`,
`ls -R`, `grep -r` or any other sweep, and above all do not sweep `/sessions/*/mnt/` — those are
the person's mounted folders. Sweeping them can force a cloud provider to materialise thousands
of files one at a time: it looks like a hang, it can silently download tens of gigabytes, and it
will not find the plugin anyway. Say "the plugin scripts are not reachable from this session"
and let the person reinstall.

**Copying the scripts to bridge two execution contexts is allowed — sweeping is not.** These are
different things and only one is dangerous:

- ❌ **Forbidden:** searching the filesystem to *find* the plugin. It can materialise thousands
  of cloud files and still not find it.
- ✅ **Allowed:** once the locator has found the plugin, copying `scripts/` and `templates/`
  into scratch space so they can run somewhere the target folder is reachable.

The second case is real. In a **cloud-linked session** the plugin lives in the cloud container
while the target folder is only reachable from the device VM — two places, no overlap. The
scripts are stdlib-only and self-locate via `__file__`, so they run correctly from anywhere:

```bash
tar -czf /tmp/rp.tgz -C "$ROOT" scripts templates .claude-plugin   # include the manifest
```

**Include `.claude-plugin/` or `plugin_version` records as `unknown`** in the vault's
`.records-project.json`. Verify the checksum after transfer, run everything from the copy, and
delete the scratch copy afterwards.

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
# 4. Cloud-linked session: plugins sync into the cloud container, NOT into /sessions/*/mnt.
#    The real layout nests the plugin name under the sync id:
#      ~/.claude/plugins/synced/<sync-id>/<plugin-name>/skills/<skill>
#    Verified 2026-09-03 — an earlier glob was one level short and printed NOT FOUND.
[ -z "$ROOT" ] && for d in "$HOME"/.claude/plugins/synced/*/*/skills/$SKILL \
                           "$HOME"/.claude/plugins/synced/*/skills/$SKILL \
                           "$HOME"/.claude/plugins/*/*/skills/$SKILL \
                           "$HOME"/.claude/plugins/*/skills/$SKILL; do
  [ -d "$d" ] && ROOT="$(cd "$d/../.." && pwd)" && break
done
# 5. Local dev.
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

## Step 2b — translate the seeded prose (non-English projects only)

`scaffold.py` renders from English templates, so a `--language Polish` vault still lands with
English folder notes and START HERE. **The person's first look at their new project would be in
the wrong language.** Translate the seeded prose in place, with the file tools, before handing
over:

- `00 START HERE.md`
- every folder note (`01 Master/01 Master.md`, `03 Inbox/03 Inbox.md`, …)
- `01 Master/Master Summary.md`, `01 Master/Settled — do not re-open.md`
- each `01 Master/Questions — <advisor>.md`
- `CLAUDE.md` — **ask first.** It is the control panel and the engine. An operator working in
  their own language wants it readable; but a mistranslation there changes behaviour rather than
  just wording. Offer it, translate it only on a yes, and if in doubt leave it English and say
  so.

**Leave these byte-for-byte identical — translating any of them breaks filing:**

| Never translate | Why |
|---|---|
| File names and folder names on disk | `scaffold.py`, `validate_vault.py`, the snapshot trigger and the skill descriptions all match these exact strings |
| Anything inside `[[ ]]`, **including the alias after `\|`** | Simplest safe rule; a translated alias is fine in theory but one slip silently breaks the link |
| Anything in backticks — paths, flags, filenames | They are literals |
| `.records-project.json` | Machine-readable |
| Dates, units, marker names, drug names, quoted source text | Quoted material keeps its original language |

Headings that are *not* wikilink targets can be translated freely.

Re-run the validator afterwards — it checks that every wikilink still resolves, which is exactly
the thing a careless translation breaks.

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
