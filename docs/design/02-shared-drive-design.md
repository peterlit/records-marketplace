# Design — shared Google Drive variant

*2026-09-01. **Design only — no code changes made.** Supersedes the earlier Slack/Drive addendum, which assumed Google-native documents; this one keeps markdown and Obsidian, which changes the architecture substantially and for the better.*

## Requirements as given

1. Shared **Google Drive** folder is the store of record.
2. Continues to generate **Obsidian-friendly `.md`** files.
3. **Claude Team** account; every member has their **own session**, reading *and writing* the same folder.
4. **Optional** Claude Tag in Slack.
5. **`MEMORY.md` lives in the folder**, not in per-account memory.
6. **Synchronisation markers** — `<date>-<time>-<user>-work-started/stopped`.
7. Decide: **separate skill vs. an option** on the existing one.

---

## 1. The constraint everything hangs on: Drive has two access paths

This is the single most important fact in the design, and it is why the earlier addendum reached a gloomier conclusion than necessary.

| | **Path A — Drive for Desktop (mounted)** | **Path B — Drive connector (API)** |
|---|---|---|
| How | Google Drive for Desktop mounts the folder as a local path | The MCP connector talks to the Drive API |
| Read | ✅ normal file tools | ✅ `read_file_content` |
| **Edit a file in place** | ✅ **yes** | ❌ **no** — `update_file` supports *only* title and parentId |
| Create / rename / move / trash | ✅ | ✅ |
| Obsidian | ✅ works | ❌ n/a |
| grep across the vault | ✅ | ❌ search API only |
| Available on | **Cowork** (desktop) | **Cowork and Claude Tag** |

**Everything follows from this.** Path A gives ordinary filesystem semantics — the entire existing design works unchanged, with Drive simply replacing iCloud as the sync provider. Path B cannot rewrite a file at all.

⚠️ **Claude Tag has no local filesystem.** It runs in ephemeral cloud sandboxes, so Slack is unavoidably Path B.

### The consequence, stated plainly

> **Cowork is the read/write/curate surface. Slack is a read-and-append surface.**

Slack members can interrogate the whole record and add new material (new files into `03 Inbox` or the chronicle — creation works fine). They cannot rewrite the Master Summary, the Settled register, or a trend table. Curation happens in Cowork.

This is an honest division rather than a limitation to engineer around. Attempting in-place editing from Slack means either a Google service account with full API access — an admin project with credential-custody problems — or replace-and-trash, which breaks every shared link and destroys comment history. **Neither is worth it.** Recommend documenting the split and designing to it.

---

## 1b. ✅ EMPIRICAL RESULTS — Path B probed against a real Drive folder (2026-09-02)

Tested in `Health-MPL-Test` via the connector. **Path A predictions unchanged; Path B is now measured, and it is more limited than §1 assumed.**

| Capability | Result |
|---|---|
| Create folder | ✅ works |
| **Create `.md` with `disableConversionToGoogleType: true`** | ✅ **stays `text/markdown`, extension `.md` — NOT converted to a Google Doc.** The markdown requirement survives on Drive. |
| Stored bytes faithful? | ✅ **yes** — 210 bytes in, 210 bytes stored. Storage is exact. |
| Rename / move | ✅ works |
| **Edit content in place** | ❌ **no such parameter exists.** `update_file` takes `fileId`, `title`, `parentId` only. |
| **Read content back** | ⚠️ **LOSSY — this is new and it matters.** |
| Sync markers (create + list by `parentId`) | ✅ works exactly as designed |

### ⚠️ The new finding: connector reads are escaped, not raw

Reading the probe file back returned:

```
\# Probe note … \- \[\[00 START HERE\]\]
```

`read_file_content` returns a *"natural language representation"*, not the bytes — markdown special characters come back escaped, and the tool's own description warns: *"The text representation will change over time, so don't make assumptions about the particular format."*

**Crucially, the file on Drive is fine.** The escaping is a *read-path* artifact, not corruption. Anything reading through the mount (Path A, Obsidian) sees the correct file.

**Consequence for Slack, which has no choice but Path B:**

- ✅ Read a file to **understand** it — the escaping is legible.
- ❌ **Quote file contents verbatim** — what comes back is not what is stored.
- ❌ **Round-trip** (read → modify → write a new version) — escaping would accumulate and corrupt.
- ✅ **Create** new files — Inbox drops, chronicle entries, sync markers.

So the Slack role narrows from "read and append" to **"comprehend and append."** The engine must tell Claude-on-Slack not to reproduce file contents verbatim and not to attempt any edit-by-replacement. This does not kill the Slack option, but it does mean Slack can never be a curation surface even in principle.

**Design rule that follows:** *on Drive, the vault is always accessed through the mount. The connector is strictly a fallback for surfaces that have no filesystem.*

## 1c. ✅ Marketplace install verified — and it exposed a real bug

The plugin was installed from a marketplace and probed live:

- Marketplace plugins mount **read-only at `/sessions/<session>/mnt/.remote-plugins/<opaque-plugin-id>/`** — **not** under `.claude/skills/`, and **the directory name is an opaque id, not the plugin name.**
- The mount is the **plugin root**: `scripts/`, `skills/`, `templates/`, `.claude-plugin/` all present.
- **Scripts execute.** `probe.py` ran; `scaffold.py` built a vault from the installed copy; `validate_vault.py` passed it.
- ❌ **The Phase-1 locator was wrong.** It was written against *built-in* plugin skills, which mount flat by skill name at `.claude/skills/<skill>/`. It had no `.remote-plugins` strategy and would have failed on every real install.

**Fixed:** the locator now tries `CLAUDE_PLUGIN_ROOT` → `.remote-plugins/*/skills/<skill>` (up two levels) → `.claude/skills/<skill>` → local dev. *This is exactly the class of bug that only a real install surfaces — the reason Phase 5 existed.*

## 1e. ✅ S1 PASSED (2026-09-02) — the vault builds, validates and snapshots on Google Drive

**The blocker in §1d was a path problem, and a symlink solved it.** Attaching the raw `~/Library/CloudStorage/GoogleDrive-<your-account>/My Drive/…` path failed to mount into the bash sandbox. Attaching **`~/gDrive/!PROJECTS/Health-MPL-Test`** — a short symlink to the same location — mounted cleanly. *Suspect the `CloudStorage` prefix, the `GoogleDrive-<email>` component, or the spaces; the fix is the same either way.*

> **Setup requirement for every member: create a short symlink to the Drive folder and attach *that*, not the raw CloudStorage path.**
> `ln -s "$HOME/Library/CloudStorage/GoogleDrive-<you>/My Drive" "$HOME/gDrive"`

### End-to-end proof, run from the plugin against the real Drive folder

```
scaffold  → preset=health folders=15 conservatism=conservative obsidian=True
validate  → checked 22 notes … vault valid
snapshot  → snapshot-2026-09-01-2227.zip: 21 files, 10,357 bytes
files 29 · zero-byte 0 · shared block rendered · Drive sync-hazard block rendered
```

### Final Drive capability matrix (all measured, none assumed)

| Operation | bash | file tools | connector |
|---|---|---|---|
| Read (raw, exact) | ✅ | ✅ | ⚠️ escaped |
| Write / create | ✅ | ✅ | ✅ |
| Create dirs | ✅ | — | ✅ |
| Build a zip (snapshots) | ✅ | — | — |
| Grep whole vault | ✅ | ✅ | ❌ |
| Edit in place | ✅ | ✅ | ❌ |
| **Delete** | ❌ **blocked** | ❌ | ✅ **`trash_file` works** |

**Two things this settles.** Drive matches iCloud's deletion block from the sandbox — *but unlike iCloud, there is a working escape hatch*: the connector can trash what bash cannot delete, verified on two real files. That closes the stray-file problem this project has lived with all year. And no 0-byte placeholders appeared, confirming offline mode is doing its job.

**Engine change to make:** in Drive mode, the cleanup instruction becomes *"delete via the Drive connector's `trash_file`"* rather than *"leave stray files for the user."*

### Two bugs found by running it for real

1. **`validate_vault.py` passed a folder that did not exist** — printed `vault valid` after checking 0 notes. Fixed: fails on a missing target, and fails if no markdown is found.
2. **The installed plugin and the repo clone are both pre-co-user (v0.2.0).** Only the `_plugin-dev` copy has shared mode. **Iteration loop needed:** dev copy → repo clone → commit → push → reinstall.

---

## 1d. ⚠️ (superseded by §1e) Path A appeared split — file tools reached Drive, bash did not

The Drive folder was attached as a Cowork workspace folder via Drive for Desktop (`~/Library/CloudStorage/GoogleDrive-…/My Drive/!PROJECTS/Health-MPL-Test`). Result:

| Operation | Works? |
|---|---|
| `Read` / `Write` / `Edit` / `Grep` / `Glob` on the Drive path | ✅ **yes** — verified: wrote a file, grepped it back, wikilinks and pipes intact |
| Reading a connector-created file through the mount | ✅ **raw and exact** — `# Probe note`, `- [[00 START HERE]]`, **no escaping**. Confirms storage is faithful and §1b's escaping is purely a connector read artifact. |
| **`bash` on the Drive path** | ❌ **BLOCKED.** *"couldn't be mounted into the bash sandbox — use Read/Write/Edit/Grep/Glob on the host path instead… or ask the user to grant the app access to this location and restart."* |

**This is the most consequential finding so far, because the entire plugin is script-based and scripts run in bash.** `scaffold.py`, `validate_vault.py` and `snapshot.py` cannot currently execute against the Drive folder.

### Three ways forward, in order of preference

1. **Grant the app access to the CloudStorage location and restart** (macOS: System Settings → Privacy & Security → Full Disk Access → enable for Claude). If this works, bash reaches Drive and **the design proceeds exactly as written — no plugin changes at all.** Try this first; it is one toggle.
2. **File-tools mode.** Scaffold and validate in sandbox scratch, then transfer the ~25 generated files to Drive with `Write`. Works today, needs no permissions, but it abandons the run-a-script model and makes snapshots awkward. Would require a `--emit-manifest` mode in `scaffold.py` so the transfer is mechanical rather than Claude retyping files.
3. **Sync a normal local folder to Drive** via Drive for Desktop → *Folders from your computer*. The vault then lives at an ordinary bash-reachable path. ⚠️ **Caveat: such folders land under Drive's "Computers" section, whose sharing model is more limited than My Drive** — which may defeat the shared-access requirement. Verify before adopting.

**Not yet known:** whether this is a permissions issue that (1) fixes, or a hard limitation of how the sandbox handles macOS `CloudStorage` virtual filesystems. Answering that is now the first task in S1.

### The clone is ready

`~/Documents/src/records-marketplace` is attached, **bash-reachable**, git history intact (`cdffeea records-project v0.2.0`), remote `github.com/peterlit/records-marketplace`, with `.privacy-patterns` present and gitignored. Iteration can happen there normally.

## 1f. Provider abstraction — designed now, Dropbox built later

*Added 2026-09-02. **Design only.** The point is not Dropbox specifically; it is that the provider choice should be **reversible**, and today it isn't — provider assumptions are scattered across `scaffold.py`, `validate_vault.py` and the engine template.*

### Good news: the design is already ~90% provider-agnostic

Everything that matters — the vault structure, templates, engine, markdown, Obsidian, snapshots, 0-byte verification, optimistic concurrency, sync markers, the whole co-user model — is plain files and cares nothing about the provider.

### The seam: six things, and only six, are provider-specific

| # | Provider-specific | Drive (measured) | Dropbox (expected) |
|---|---|---|---|
| 1 | **Mount path shape** | ⚠️ needs a `~/gDrive` symlink; raw `CloudStorage/…` won't mount | `~/Dropbox/…` — plain, likely mounts directly |
| 2 | **Conflict-copy filename patterns** | `(1)`, `(2)` | `(conflicted copy)`, `(Case Conflict)` |
| 3 | **Placeholder / offline mode** | must set **"Available offline"**; streaming yields empty reads | Smart Sync "online-only" is the equivalent hazard |
| 4 | **Connector** | Google Drive MCP — `trash_file` ✅ *(verified)*, reads escaped ⚠️ | Dropbox MCP exists (`mcp.dropbox.com`): `create_file`, `create_folder`, `copy`, **`delete`**, `create_shared_link` — **unverified** |
| 5 | **Sharing mechanism** | share folder / Shared drive | shared folder invite |
| 6 | **Setup prose in the generated `CLAUDE.md`** | Drive wording | Dropbox wording |

Note items 2 and 3 differ per provider but are the *same shape* of problem — which is exactly what makes a data-driven profile the right abstraction.

### The abstraction: provider profiles as data, mirroring domain presets

Reuses a pattern already proven by `presets/`:

```
templates/providers/
  gdrive.json   dropbox.json   icloud.json   onedrive.json   local.json
```

Each profile carries: display name · path hint and any **mount caveat** · offline-mode requirement · **conflict-copy regex list** · connector name and what it can do · sharing steps · known hazards prose. `scaffold.py --cloud dropbox` loads the profile and renders the engine from it; nothing provider-specific stays hard-coded.

### The piece that makes it reversible: the vault must describe itself

Add **`.records-project.json`** at the vault root:

```json
{ "plugin_version": "0.3.0", "created": "2026-09-02",
  "preset": "health", "provider": "gdrive",
  "shared": true, "co_users": ["the maintainer", "Co-user Two"],
  "obsidian": true, "snapshot_trigger": "master" }
```

This is worth doing **regardless of Dropbox**. Today `validate_vault.py` guesses conflict patterns by trying all providers at once, and `file-to-records` / `records-gap-audit` infer settings by reading prose. A self-describing vault ends that — every tool reads its configuration instead of inferring it.

### Migration: `scaffold.py --reconfigure`

Moving providers is then: copy the folder, then

```bash
python3 scaffold.py "<new path>" --reconfigure --cloud dropbox
```

which **rewrites only the engine and the config** — `CLAUDE.md` hazard block, `.records-project.json` — and touches **no content**. That is the escape hatch that makes the provider choice non-permanent, and it is the actual deliverable of this section.

⚠️ `--reconfigure` must refuse to run unless `.records-project.json` exists, so it can never be mistaken for a fresh scaffold over live data.

### Also folds in the deletion correction

Profiles carry `delete_via`. **Corrected 2026-09-02:** the deletion block is **Cowork's protection, not the provider's** — verified blocked on plain local disk and in `outputs`, not just cloud mounts. The right answer everywhere is **`allow_cowork_file_delete`**, with the connector (`trash_file` / `delete`) as a provider-specific fallback. *The current templates say "expect deletion to be blocked, leave strays for the user" — that guidance is wrong and needs replacing.*

### Cost

Small, and mostly repaid immediately: extract ~6 hard-coded provider assumptions into JSON, add `.records-project.json`, teach the validators to read it, add `--reconfigure`. **Building the Dropbox profile itself is then a single JSON file plus one real test.** Nothing here requires deciding about Dropbox now.

## 2. Architecture

```
Google Drive  ▸  "Shared drive" or a shared folder
└── <Project>/                     ← the vault, plain .md throughout
    ├── CLAUDE.md                  engine
    ├── MEMORY.md                  shared memory index      ← new
    ├── memory/                    shared memory topic files ← new
    ├── _sync/                     presence markers          ← new
    ├── 00 START HERE.md
    ├── 01 Master/  02 Chronicle/  03 Inbox/  04 Critiques/
    ├── 05 Trends/  06 Reference/  07 Deep Dives/  99 Archive/
    └── .obsidian/                 (see §6 — needs care)

Access:
  Team member on Cowork  →  Drive for Desktop mount  →  full read/write  →  Obsidian ✅
  Team member in Slack   →  Drive connector          →  read + create    →  Obsidian ✗
```

**Drive-specific setup requirements** (these are real and specific, not boilerplate):

- Each Cowork member installs **Google Drive for Desktop** and marks the project folder **"Available offline."** Streaming mode leaves placeholder files that Obsidian's indexer and file-watcher handle badly, and that Cowork may read as empty — the same class of failure as iCloud's 0-byte cloud-only files, which this project has already been bitten by.
- Use a **Shared drive** (team-owned) rather than one person's *My Drive* folder. Files in a personal Drive belong to that person; if they leave the org, ownership becomes a problem.
- Each member attaches the mounted path as a Cowork **workspace folder**.

---

## 3. Shared `MEMORY.md` — good idea, with one clarification

Storing memory in the folder is the right call and solves the divergence problem directly. One thing to be precise about:

**Claude's *account* memory cannot be redirected into a folder.** It is per-user and stays that way. So `MEMORY.md` is a **project memory file the engine reads**, not a replacement for the account feature. That is better, not worse — it is inspectable, diffable, snapshot-able, and shared by construction.

The engine rule becomes:

> **Read `MEMORY.md` and the relevant `memory/*.md` files at the start of every session. Write durable facts there — never to account memory. If account memory and a file disagree, the file wins.**

**Structure — mirror what already works here:** `MEMORY.md` as a one-line-per-entry index, plus `memory/<topic>.md` topic files. This matters for concurrency: two sessions usually touch *different* topics, so topic files rarely collide, whereas a single monolithic memory file is a guaranteed collision point. The index is append-mostly.

⚠️ **Do not put memory in a Slack-writable path expecting Slack to update it** — Path B cannot rewrite `MEMORY.md`. Slack sessions read memory and *append* observations to the chronicle; a Cowork session folds them in.

---

## 4. Synchronisation markers — honest assessment

Your instinct is sound, and the format is well chosen: **creation-only, uniquely named files never collide on any sync provider or either access path.** They work identically in Cowork and Slack. That is a real advantage over anything requiring a lock file to be *modified*.

### Proposed shape

```
_sync/2026-09-01T14-22-05Z__peter__started.md
_sync/2026-09-01T15-04-11Z__peter__stopped.md
```

Body: session id, surface (cowork/slack), and a one-line intent — *"filing the 8/12 labs"*. That last field is what makes the marker useful to a human rather than just to the machine.

### What they are good for

- **Presence** — "Maria started 12 minutes ago and hasn't stopped" is genuinely useful before you begin rewriting the Master Summary.
- **Audit** — who worked when, across surfaces, permanently.
- **Zero-cost** — no locking primitive needed, works everywhere.

### ⚠️ What they are *not*

**They are advisory, not a mutex.** Four specific weaknesses, all of which should be documented rather than papered over:

1. **Race window (TOCTOU).** Two sessions can both list `_sync/`, both see nothing, and both start. Narrowable — write your marker, wait ~5 s, re-list, and if someone else's marker appeared with an earlier timestamp, defer — but never eliminated.
2. **Sync latency is the real killer.** Drive propagation is seconds to minutes. During that window your marker is invisible to everyone else, and theirs to you. **This makes markers unreliable as a lock over exactly the interval where a lock would matter.**
3. **Stale markers.** A crashed session or closed laptop leaves `started` with no `stopped`. Needs a **TTL — treat anything older than ~4 hours as expired** — or the folder accumulates phantom locks that everyone learns to ignore.
4. **Wrong granularity.** A whole-project marker blocks a colleague who only wants to *read*, while the actual risk is two people editing the *same file*.

### Recommendation

**Use markers for presence and audit. Do not rely on them for safety.** Pair them with the mechanism that actually catches the problem:

> **Optimistic concurrency on curated files.** When a session reads a file it intends to modify, record its size and modified-time (or a content hash). Immediately before writing, re-read. If it changed, **do not overwrite — merge, and say in the Prompt Log that you merged.** This catches the collision regardless of whether either party saw the other's marker.

That is a handful of lines in the engine, it has no race window, and it degrades gracefully. Markers make collisions *rarer and visible*; optimistic concurrency makes them *safe*.

**Plus the existing defence:** `validate_vault.py` already detects Drive/Dropbox conflict copies and refuses to proceed. Run it at session start in shared mode.

---

## 5. Separate skill vs. an option — the comparison you asked for

### Option A — a separate skill

| Pros | Cons |
|---|---|
| Clean triggering: *"set up a shared project for our team"* is genuinely different phrasing from the solo case | Content duplication; the two drift apart over time |
| Its own interview: Drive setup, Team roster, Slack, marker policy | Two descriptions to tune — and triggering is already the least-tested part |
| Solo users never see team complexity | Users must pick, and may pick wrong |
| Failure isolation | Two skills to maintain |

### Option B — an option on the existing skill

| Pros | Cons |
|---|---|
| One source of truth for templates and scripts | The description must cover both, diluting trigger quality — the known failure mode for skills |
| **Natural upgrade path** — a solo project becomes shared without re-bootstrapping | Interview grows more branching |
| One skill to maintain and evaluate | Solo users see complexity they don't need |

### ✅ Recommendation: split the *skills*, share the *machinery*

Neither pure option is right. The expensive, correctness-critical parts are the **templates and scripts** — those should stay unified, with `scaffold.py` gaining `--store gdrive|local` and `--surface cowork|cowork+slack`. Skills are cheap prose wrappers, and their only real job is triggering well.

So:

- **`bootstrap-records-project`** — unchanged, solo, tight description.
- **`bootstrap-shared-records-project`** — new, thin. Owns the team conversation: Drive setup, offline-mode requirement, roster, marker policy, Slack yes/no. Calls the *same* `scaffold.py`.
- **`records-sync-status`** — new, small. Reads `_sync/`, reports who is active, flags stale markers, runs the conflict check. Useful on both surfaces and cheap to build.
- **`file-to-records`, `records-gap-audit`, `records-critique`** — unchanged; they read the engine and behave accordingly.

This gets clean triggering *and* one implementation. It also means a solo project can be upgraded later by re-running the scaffolder in shared mode over an existing folder — worth designing for explicitly.

---

## 6. ⚠️ Obsidian on a shared Drive — the part most likely to annoy

- **`.obsidian/workspace.json` rewrites constantly** as anyone scrolls or opens a pane. With several members syncing it, expect **conflict copies daily**. That noise trains people to ignore conflict warnings — precisely the wrong habit, given that a *real* conflict in `01 Master` looks the same.
  **Recommendation: exclude `.obsidian/` from sync**, or keep only `.obsidian/plugins/folder-notes/data.json` and `community-plugins.json` (stable) and let each member hold their own workspace state locally. Needs testing on Drive for Desktop, which has weaker selective-sync than Dropbox.
- **"Available offline" is mandatory**, per §2.
- Folder notes and wikilinks work exactly as now — this is why Path A is worth the setup cost.

---

## 7. Team and Slack specifics

**Team plan.** Cowork projects are **not shareable** and memory is **per-user** — both documented. Neither matters here, because the folder is the shared object and `MEMORY.md` replaces account memory. What Team *does* buy: org-provisioned plugins and skills, so every member's Cowork behaves identically without each person installing anything. That is the real reason to be on Team for this.

**Claude Tag (optional).** Team/Enterprise only. Channel-scoped session and memory; **service identity, not per-user** — so Claude in Slack cannot act as the individual, and channel members all share one permission set. Slack sessions:

- read the record through the Drive connector,
- answer questions,
- **create** new files (Inbox drops, chronicle entries, `_sync` markers),
- **cannot** rewrite curated files.

⚠️ **Before enabling Slack**, settle the compliance question: putting health records into a Slack workspace brings retention, eDiscovery and admin-visible channel memory into scope. Not a blocker; a decision to take deliberately.

---

## 8. Engine changes (`CLAUDE.md` template)

New conditional block for shared mode:

- Read `MEMORY.md` + `memory/*.md` at session start; **files beat account memory**.
- Read the last N `Prompt Log` entries — the shared conversation.
- **Write a `_sync` started marker; write a stopped marker when done.** Check for others' active markers first and *report* rather than block.
- **Optimistic concurrency** rule for curated files: re-read before write, merge on change, log the merge.
- Run the conflict-copy check at session start; stop if any are found.
- Attribute everything — Prompt Log `Who` column, "reported by" on Timeline entries.
- Surface awareness: *if you are on Slack, you cannot rewrite curated files — append and hand off.*

---

## 9. Risks, ranked

1. **Sync latency defeats markers as a lock.** Mitigated by optimistic concurrency, not by better markers. *Accept and document.*
2. **Streaming-mode Drive produces empty reads.** Same failure class as iCloud 0-byte files. *Mandate "Available offline"; keep the size>0 checks.*
3. **`.obsidian` conflict noise desensitises everyone to real conflicts.** *Exclude it; needs testing.*
4. **Slack's create-only limit surprises someone mid-task.** *State it in the engine so Claude says so upfront.*
5. **Trigger dilution across two bootstrap skills.** *Evals, which are already the outstanding gap.*
6. **PHI in Slack.** *Decide before enabling.*

---

## 10. Proposed build order

| Phase | Work | Proves |
|---|---|---|
| **S1** | Spike Path A only: Drive for Desktop mounted, offline mode, one Cowork member, existing scaffolder unchanged | That Drive replaces iCloud cleanly and Obsidian survives |
| **S2** | `MEMORY.md` + `memory/` in-folder; engine reads them | Shared memory works before concurrency exists |
| **S3** | `_sync` markers + `records-sync-status` + optimistic-concurrency rule; test with two members deliberately colliding | The safety story, empirically |
| **S4** | `.obsidian` exclusion strategy; multi-member Obsidian test | The annoyance is controlled |
| **S5** | `bootstrap-shared-records-project` + `--store gdrive` in the scaffolder | One-command setup |
| **S6** | Slack, if still wanted: connector read/append path, surface-aware engine rules | The optional surface |

**S1–S3 are the whole value.** S6 is genuinely optional and the most expensive.

---

## 11. Open questions

1. **Is anyone actually on Team yet**, or is this contingent on buying it?
2. **Shared drive or shared folder?** Recommend a Shared drive for ownership reasons — needs Workspace, not consumer Gmail. ⚠️ *Your account is `@gmail.com`; Shared drives require Google Workspace.* Worth confirming before designing around it.
3. **Does the existing project migrate to Drive, or is this for a second person?**
4. **Marker granularity** — whole-project, or per-area (`01 Master` vs the rest)? I lean whole-project for simplicity, since markers are advisory anyway.
5. **Does Slack stay in scope?** It roughly doubles the design surface for a read-and-append capability.
