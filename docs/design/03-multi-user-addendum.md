# Design addendum — multi-user variant: Claude Tag in Slack + Google Drive

*2026-08-08. Companion to [[2026-08-08 Plan — Records Project Bootstrapper plugin|the bootstrapper plan]]. Question: can several people work the same records project by tagging Claude in Slack, with the structure living in Google Drive?*

**Short answer: yes — but it is a different architecture, not a preset.** Two facts force the change, and one of them is a hard capability limit I verified rather than assumed.

---

## 1. Settled preferences from the last round (now folded into the design)

| # | Decision |
|---|---|
| 1 | **Repo public.** |
| 2.1 | **Do not assume the user is the decision-maker** — ⚠️ this now becomes *load-bearing*, see §7 |
| 2.2 | Present steelmanned options, not directives |
| 2.3 | Limited-trust framing for advisors |
| 2.4 | **Conservatism on invasive procedures = a dial**, not a constant |
| 3 | Memory written **only on explicit yes** in the interview |
| 4 | **Obsidian optional** — ⚠️ and in this variant, off by default |
| 5 | `file-to-records` deliberately duplicates the generated `CLAUDE.md` — confirmed |

---

## 2. ⚠️ The finding that determines the whole design

**The Google Drive connector cannot edit a file's contents.** From the tool schema, verbatim:

> `update_file` — *"Request to update a file (currently only title and parent_id are supported)."*

The full capability set is: **create** (with content; can create folders and native Docs/Sheets/Slides), **read**, **rename/move**, **copy**, **share**, **trash**. There is no write-into-existing-file operation.

This kills the current model outright. Today's `Master Summary` is *"overwritten in place as things change"* — that operation does not exist against Drive. The only way to "update" a Drive file through the connector is to create a replacement and trash the original, which **breaks every shared link, resets Drive's version history, and destroys the comment threads** attached to the old file. Doing that to a document three family members have bookmarked is not acceptable.

So the architecture must become **create-only**. Fortunately that is also the correct answer for concurrency (§6) — the constraint and the requirement point the same way, which is usually a sign the design is right rather than merely tolerable.

*Caveat: Claude Tag also has bash and a code sandbox, so a workspace admin could provision a Google service account and drive the full Drive API directly, restoring in-place edits. That's a real option but it's an admin project with its own credential-custody problem, and it is out of scope for something installed from a marketplace. Noted in §10.*

---

## 3. What Claude Tag actually gives us

Confirmed from Anthropic's documentation:

| Property | Reality | Consequence for this design |
|---|---|---|
| **Availability** | **Team & Enterprise only** (beta as of Aug 2026). Not Pro, not Max, not Free. | ⚠️ **Precondition.** If you're on Pro/Max this variant is unavailable today. |
| **Session model** | Channel-level session; a task needing tools **spawns a thread that binds to its own session**. Threads don't share state with each other. | The unit of "project" is the **channel**, not the thread. |
| **Memory** | **Persistent, scoped per channel and workspace.** Private-channel learning never leaks to the workspace. **Admins can view, edit and delete it.** | Channel memory replaces the local memory files — but see the privacy note in §4. |
| **Context** | Reads channel history; "most of the briefing is already done" | The Prompt Log's purpose is partly served by the channel itself. |
| **Identity** | **Service identity, not the tagging user.** Distinct identity per private channel; public channels share a workspace identity. | ⚠️ **No per-user Drive permissions.** Everyone in the channel gets identical access. Access control is the *channel roster*, nothing finer. |
| **Tools** | Connectors (incl. Google Drive), bash, code execution, Skills, Plugins, MCP | The plugin can ship here. |
| **Concurrency** | **Undocumented.** No public spec on simultaneous mentions, queuing, or rate limiting. | ⚠️ We must design as if there is **no** concurrency protection. §6. |

---

## 4. ⚠️ Before any of this: the compliance question

Moving one person's medical records into a Slack workspace and a shared Drive changes the risk picture completely, and it is worth being blunt about it:

- **Slack is not HIPAA-eligible by default** — it requires specific paid plans plus a signed BAA. Same question applies to the Anthropic side for Team/Enterprise.
- **Claude Tag's channel memory is admin-viewable and admin-editable.** A workspace admin can read what Claude has learned about the patient in a private health channel. That is a reasonable design for a company; it is a surprising one for a family's medical data.
- **Slack retention and eDiscovery** apply to whatever gets posted. Lab values pasted into a channel are in the workspace's retention system.
- **Membership drift** — people join and leave channels. Drive shares outlive Slack membership unless someone actively reconciles them.

None of this is a blocker. It is a decision to make deliberately rather than discover later. **If this is for a family rather than an organisation, a dedicated workspace with a small closed private channel, minimal retention, and a named admin is the sane setup** — and the plugin's interview should say so out loud rather than silently scaffolding PHI into a corporate Slack.

*Not legal advice — worth a real answer from whoever owns compliance for the workspace.*

---

## 5. Markdown + Obsidian in Drive? Mostly no — split by who reads it

**Obsidian: drop it for this variant.** Not a close call.

- It is a **local-first, single-user** application. Drive for Desktop presents a virtual filesystem that Obsidian's file-watching handles poorly.
- Multi-user sync of a vault produces **conflicted copies** — Drive resolves collisions by duplicating files, which is exactly wrong for a vault whose links depend on filenames.
- The `.obsidian/` config directory itself gets sync-conflicted between users.
- **Wikilinks render as literal `[[text]]` in Drive's web UI.** The entire navigation model — the thing you actually liked — evaporates for anyone not running Obsidian locally.

**Markdown: keep it only where Claude is the sole consumer.** The right split is by audience:

| Content | Format | Why |
|---|---|---|
| **Engine + templates** (`CLAUDE.md`, skill files) | **Markdown** | Only Claude reads them. Plain text is correct. |
| **Documents humans read and discuss** — Master Summary, question lists, critiques, deep dives | **Google Docs** | Comments and suggestions, **real version history** (better than our zip snapshots), mobile access, no app to install, granular sharing. Non-technical family members can actually use it. |
| **Longitudinal numbers** — Trends | **Google Sheets** | Genuinely better than markdown tables: sorting, filtering, charts, per-cell revision history, and concurrent editing that *works*. This is an upgrade, not a compromise. |
| **The event ledger** (§6) | **Markdown or JSON**, one file per event | Machine-written, never hand-edited, immutable. |
| **Raw archive** | **As received** | Never converted, never touched. |

Navigation without wikilinks: Drive folders plus a single **"START HERE" Google Doc** carrying real hyperlinks to each document's Drive URL. Less elegant than a vault, but it works for everyone with a browser. The plugin generates and regenerates it.

**One person can still have both.** If a steward wants the Obsidian experience, they run the local variant against a Drive-synced copy for *reading*, while all writes go through the Slack/Drive path. Do not attempt bidirectional sync.

---

## 6. Concurrency — the actual design

### The threats

1. **Lost update** — two sessions read Master Summary, both write, one silently clobbers the other.
2. **Split-brain Settled register** — the one file whose entire purpose is to be a single source of truth about what's been adjudicated.
3. **Duplicate filing** — two people upload the same lab PDF; it gets filed twice under different names.
4. **Contradictory content** — the daughter reports the cardiologist said X; the spouse reports Y. Not a write race; a genuine disagreement.
5. **Authority ambiguity** — who is entitled to mark something settled, or to record a decision?

Threats 1–3 are mechanical. 4–5 are human, and **must not be auto-resolved.**

### The move: append-only ledger + derived projections

Stop treating the Master Summary as a document that gets edited. Treat it as a **projection** of an immutable event log.

```
04 Ledger/                        ← append-only, never modified, concurrency-safe
  2026-08-08T14-22-05Z__anna__result__a4f21c.md
  2026-08-08T14-22-58Z__peter__decision__9bd077.md
  2026-08-08T15-02-11Z__anna__correction__31ce90.md

01 Master/                        ← PROJECTIONS. Regenerated, never hand-edited.
  Master Summary          (Google Doc)
  Settled — do not re-open (Google Doc)
  Needs adjudication       (Google Doc)   ← new
05 Trends/                (Google Sheet)
```

**Why this fixes 1–3 by construction:**

- Every write is a **new file with a globally unique name** (ISO timestamp + author + content hash). Two concurrent writers cannot collide, because they never target the same object. No locks, no leases, no retries.
- It **fits the connector exactly** — create-only is all we have, and all we need.
- **Duplicate detection is free**: the filename carries a content hash. If a ledger entry with that hash exists, skip. Threat 3 solved.
- **Nothing is ever lost.** A bad entry is superseded by a correction event, not deleted. Given how much of this project's value came from *catching* wrong corrections, an audit trail of who asserted what, when, is worth more here than in the solo version.

**The projections are rebuilt by a single serialized reconciler.** Because it is the only writer of the projection documents, there is no write contention to manage. Run it on a schedule (Cowork/Claude Tag can hold a scheduled task) rather than on every mention — that removes the need for locking entirely, at the cost of the Master Summary lagging the ledger by one cycle. Post a one-line "reconciled, 3 new entries, 1 needs adjudication" note to the channel each run.

**Projection updates still can't edit in place** — so the reconciler *creates a new revision file and moves the previous one to `99 Archive/`, keeping the canonical document's Drive ID stable by writing content into a Doc that humans own.* ⚠️ **This is the one piece that needs a real answer** — see §10, open question 1. The honest position today is that Doc-content updates require either the service-account route or accepting a "latest revision" file per projection.

### Genuine conflicts are surfaced, never resolved

When the reconciler finds two ledger entries asserting incompatible facts about the same subject, it does **not** pick one. It:

1. writes both into **`Needs adjudication`** with author and timestamp,
2. posts to the Slack channel tagging the **steward**,
3. leaves the Master Summary showing the *last adjudicated* state, explicitly flagged as contested.

Adjudication is itself a ledger event, authored by the steward. **The Settled register only accepts entries whose author has the steward role** — that's what stops the split-brain in threat 2.

---

## 7. Roles — why "don't assume the user is the decision-maker" now matters

In the solo project, you are patient, decision-maker and operator at once. In a family channel those come apart, and **Claude Tag's service identity means Claude cannot infer authority from permissions** — every channel member looks identical to it. Authority has to be explicit data.

A roster file maps Slack user IDs to roles:

| Role | Can do |
|---|---|
| **Patient** | Everything; final say on their own care |
| **Proxy / decision-maker** | Adjudicate, settle, record decisions — named explicitly, not assumed |
| **Steward** | Operate the system: reconcile, file, correct clerical errors. **Not** a clinical decision-maker |
| **Contributor** | Add events — upload results, report what a doctor said. Cannot settle or decide |
| **Observer** | Read only |

Claude reads the Slack message author, looks up the role, and refuses out-of-role actions with a pointer to who *can* do it. It also changes tone: to a contributor, Claude presents options and says who decides; it does not address them as the decision-maker.

**The conservatism dial** (2.4) becomes a per-project setting recorded in the roster header, set by the patient or proxy — not a constant baked into the preset, and not something a contributor can change.

---

## 8. Changes to the plugin

The clean seam is a **storage adapter** plus a **collaboration profile** — orthogonal to the domain preset:

```
preset:        health | generic          (what folders/vocabulary)
adapter:       local-fs | gdrive         (where things live, how writes work)
collaboration: solo | shared             (roles, ledger, reconciler)
```

| Component | Change |
|---|---|
| `scaffold.py` | Gains an adapter. `local-fs` = today's behaviour. `gdrive` = create folder tree via connector, create native Docs/Sheets, generate the START HERE doc with real hyperlinks, skip Obsidian entirely. |
| **New:** `ledger.py` | Append an event; compute content hash; detect duplicates. |
| **New:** `reconcile.py` | Fold the ledger into projections; detect contradictions; emit the adjudication list. |
| **New skill:** `records-reconcile` | Runs the reconciler, posts the channel summary. Scheduled, not ad-hoc. |
| **New skill:** `records-adjudicate` | Steward/proxy-only. Settle, unsettle, resolve a contradiction. Checks the roster. |
| `bootstrap-records-project` | Interview gains: adapter, collaboration mode, roster and roles, steward, conservatism dial, **and the §4 compliance prompt.** |
| `records-critique`, `records-gap-audit` | Mostly unchanged — they read projections and write ledger events like anything else. |
| **Snapshots** | Largely obsolete in `gdrive` mode: the ledger *is* the history, and Drive keeps native version history. Keep a periodic export for portability. |

---

## 9. What we lose

Worth being honest, because the solo version is genuinely nicer to use:

- **The Obsidian vault** — graph view, folder notes, instant local search, wikilink navigation. All of it.
- **Grep.** Whole-project regex search across a local folder is the operation this project has leaned on hardest — including for the "check whether it's already settled" rule. Against Drive it becomes API calls, slower and fuzzier.
- **Snapshot-and-diff.** Comparing two zips is trivial; comparing Drive states is not.
- **Single-writer simplicity.** Every operation gets more machinery.
- **Immediacy** — the Master Summary now lags the ledger by a reconcile cycle.

**Recommendation: build the shared variant as a genuinely separate mode, and don't try to make one codebase feel native to both.** Shared core templates and domain presets; different adapters, different navigation, different guarantees.

---

## 10. Open questions

1. ⚠️ **How do canonical documents get updated?** The connector can't write into an existing Doc. Options: (a) service-account + full Drive API — powerful, but credential custody and an admin project; (b) "latest revision" files with a stable START HERE doc pointing at the newest — link churn but no admin work; (c) humans own the Docs, Claude only ever appends to the ledger and posts summaries into Slack. **(c) is the most honest for v1** and I'd lean there. Your call.
2. **Is this even reachable?** Claude Tag is Team/Enterprise. Are you on one, or would this mean an org purchase?
3. **Who is the patient here?** If this is a real second person, their consent to a multi-person channel — and to admin-visible memory — should precede the build.
4. **One channel per project, or one per topic?** Channel is the memory boundary, so one channel per patient is probably right; per-topic channels would fragment memory.
5. **Does the solo variant stay the primary?** I'd suggest yes — ship solo first, since it's nearly done and it's the one proven to work.

---

# Part B — the no-Slack option: Team Cowork only

*Added 2026-08-08 in response to: "just the Team Claude login in Cowork — does that allow multiple people to work in the same project?"*

## B1. Direct answer: no. And it's documented, not inferred

Anthropic states it three times, in three places:

> **"For members of Team and Enterprise plans, Cowork projects do not support project sharing."**
> **"No session sharing: Sessions can't be shared with others."**
> **"Projects live on your computer. They aren't synced to the cloud or shared with other people."**

The Cowork docs' own capability table lists *"Shareable with teammates: **No**."* There is no multiplayer, hand-off, or co-presence feature in Cowork — I had the docs checked end to end, and there is no collaboration page at all.

Memory is likewise **per-user**: each project has its own memory space, scoped to that person's account. Org owners cannot even view it. **There is no team or shared memory anywhere in the product except Claude Tag's channel memory** — which is exactly the thing you'd be giving up by dropping Slack.

Connectors are also per-individual: each member authenticates as themselves. Enterprise-managed auth (Okta, Team + Enterprise) centralises *provisioning*, not identity — and **Google Drive isn't on the supported connector list for it** anyway.

## B2. What a Team plan *does* share

Three real things, and they're not nothing:

| Shared | Not shared |
|---|---|
| **A claude.ai project** — knowledge files, custom instructions, artifacts. *Can view* / *Can edit* permissions. | **Chats within it.** Private unless individually shared. |
| **Org-provisioned skills and plugins** — an Owner uploads once and it lands in *everyone's* Cowork, enabled by default. | Cowork projects, sessions, folders, memory. |
| **Live artifacts** — org-wide links; the viewer uses *their own* connectors. | — |

So on Team Cowork you can share **the method and the reference material. You cannot share the workspace.**

## B3. ⚠️ For coordination, this is *worse* than the Slack version

Counter-intuitive but important:

| | Claude Tag (Slack) | Team Cowork |
|---|---|---|
| Shared memory | ✅ channel-scoped | ❌ per-user, isolated |
| Shared session | ✅ channel + threads | ❌ none |
| Shared project object | ✅ the channel | ❌ explicitly unsupported |
| Coordinating agent | ✅ **one** service identity | ❌ **N independent agents** |
| Shared knowledge base | via channel | ✅ shared claude.ai project (read-only into Cowork) |
| Shared method | ✅ plugins | ✅ plugins + org skills |
| Concurrency handling | undocumented | undocumented — **and arbitrated by your sync client, not by Claude** |

With Claude Tag there is at least *one* agent with *one* memory watching the channel. With Team Cowork there are **N separate Claudes, each with its own memory, none aware the others exist**, all writing into a folder whose conflict resolution is Dropbox's or Drive's — typically **conflicted-copy files or last-write-wins**. Nothing detects it. Anthropic makes no claims either way.

## B4. But it's better in every other respect

- **Local folders work** — the whole existing design survives.
- **Obsidian still works** for each person locally. The vault, folder notes and wikilinks all keep functioning.
- **Grep still works** — and whole-project search is the operation this project leans on hardest, including for the "is it already settled?" rule. That was the single biggest loss in the Drive design; here it's retained.
- **Zip snapshots still work.**
- **No compliance question about posting PHI into a Slack workspace**, and no admin-viewable channel memory. For family medical data that's a meaningful simplification.
- **No Slack admin project**, no workspace pairing, no channel identity model.

## B5. ✅ The design decision that already pays off

**The Settled register is a file in `01 Master/`, not a memory entry.** That was written to stop *me* re-opening adjudicated questions — but it's exactly what makes multi-user viable, because memory is per-user and files are shared. Anything that must be true for everyone has to live in the folder.

**The rule this generalises to: memory is a per-person convenience, never a source of truth.** In the shared variant, the generated `CLAUDE.md` should say so explicitly, and every fact that matters must be written to a file.

## B6. Why the ledger matters *more* here, not less

With no shared agent and no shared memory, **the folder is the only coordination substrate.** So make writes non-conflicting by construction:

- **Append-only events with globally unique filenames** (`ISO-timestamp__author__type__hash.md`) — two people writing simultaneously produce two different files. **No sync client can conflict them**, because a conflict requires two writes to the same path. This works identically on Dropbox, Drive, OneDrive or iCloud, with no API involved.
- **Projections rebuilt by exactly one person's Cowork** — a designated steward, ideally on a schedule. Everyone else appends; one machine reconciles.
- **Conflicted-copy detection as a first-class check.** `validate_vault.py` gains a scan for sync-conflict filename patterns — `*(conflicted copy)*`, `* conflicted copy *`, `*-conflict-*`, `* (1).md` — and refuses to reconcile until they're resolved. Cheap, and it catches the exact failure mode.
- **Everything mutable is a projection.** If a human hand-edits a projection, the next reconcile overwrites it; the file header says so in one line.

## B7. Sync-provider caveat

Cowork documents Windows mapped drives and macOS `/Volumes/` mounts. **iCloud's on-demand/evicted-file behaviour is not documented at all** — and this project has already been bitten by it three ways: files copying as **0 bytes** when cloud-only, deletion blocked, and the `zip` binary failing on rename. For a *shared* folder I'd choose **Dropbox or Google Drive for Desktop over iCloud**, and keep the existing size-verification check regardless. None of the three is documented as supported for concurrent Cowork access.

## B8. Recommendation

**Team Cowork is the better starting point than Slack** — for family medical records specifically, and given the solo build is nearly done.

| | Slack/Claude Tag | **Team Cowork** |
|---|---|---|
| Reuses the built design | ~40% | **~90%** |
| Obsidian, grep, snapshots | lost | **kept** |
| Compliance surface | large | small |
| Coordination guarantees | weak | **weaker — must be built** |

The shape:

1. Everyone on **Team**; each person creates their **own** Cowork project pointing at the **same synced folder**.
2. The **plugin, org-provisioned**, makes every instance behave identically — this is what substitutes for a shared agent.
3. A **shared claude.ai project** carries background knowledge, linked into each Cowork project.
4. **Append-only ledger** + **one designated reconciler** + **conflicted-copy detection**.
5. **Roles live in a roster file**, since there is no identity signal at all — Cowork can't even tell you who is typing. ⚠️ Weaker than Slack, which at least supplies the message author. **Each person's Cowork must be told who they are at project setup**, and that's honour-system.

**The honest limitation:** without a shared agent, this is *cooperative* rather than *enforced*. It works well for a small, trusting group — a family — where concurrent edits are rare and everyone wants the same outcome. It is not a control system, and shouldn't be sold as one.

---

*Sources: [Cowork projects](https://support.claude.com/en/articles/14116274-organize-your-tasks-with-projects-in-claude-cowork) · [Organize work with projects](https://claude.com/docs/cowork/guide/projects) · [Get started with Cowork](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork) · [Cowork on Team and Enterprise](https://support.claude.com/en/articles/13455879-use-claude-cowork-on-team-and-enterprise-plans) · [Manage project visibility and sharing](https://support.claude.com/en/articles/9519189-manage-project-visibility-and-sharing) · [Provision and manage skills](https://support.claude.com/en/articles/13119606-provision-and-manage-skills-for-your-organization) · [Authorize MCP connectors org-wide](https://support.claude.com/en/articles/15537633-authorize-mcp-connectors-for-your-entire-organization) · [Desktop and filesystem access](https://claude.com/docs/third-party/claude-desktop/local-access) · [What is Claude Tag?](https://support.claude.com/en/articles/15594475-what-is-claude-tag) · [How Claude Tag works](https://claude.com/docs/claude-tag/concepts/how-it-works) · [Agent identity: a new access model](https://claude.com/blog/agent-identity-access-model) · [Restrict where Claude Tag operates](https://claude.com/docs/claude-tag/admins/restrict-access) · [Use Google Workspace connectors](https://support.claude.com/en/articles/10166901-use-google-workspace-connectors) · [Use connectors to extend Claude's capabilities](https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities)*
