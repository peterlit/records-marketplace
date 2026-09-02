# Plan — "Records Project" bootstrapper plugin

*Drafted 2026-08-08. Goal: package the structure + workflow that has worked here so it can be stood up for another person in a fresh project, in minutes rather than months.*

**Decisions taken (2026-08-08):** general-purpose core **+ health preset** · **full plugin with marketplace structure** · **interview-then-build** setup.

---

## 1. What we are actually packaging

The valuable part is not the folder tree — that took an hour. It is the accumulated operating knowledge. Inventory of what exists here and is worth carrying:

| Asset | Where it lives now | Generalizes? |
|---|---|---|
| **Folder architecture** (Master / Chronicle / Inbox / Critiques / Trends / Reference / Deep Dives / Archive) | the tree | ✅ fully — domain-neutral |
| **Workflow engine** — start-of-chat reading order, Type A/B message classification, announce-what-you-filed, override keywords (`log only`, `full update`, `no snapshot`, `quiet`, `orient`) | `CLAUDE.md` (60 lines) | ✅ fully |
| **Settled register + "check before correcting" rule** | `01 Master/Settled — do not re-open.md` | ✅ fully — arguably the highest-value item, and it took three repeat errors to earn |
| **Snapshot mechanics** incl. the iCloud workarounds (`zip` binary fails on rename → build with Python `zipfile` in scratch then copy; verify size > 0 because cloud-only files copy as 0 bytes; deletion is blocked) | `CLAUDE.md` + hard experience | ✅ fully — pure gold, undocumented anywhere else |
| **Obsidian + Folder Notes conventions** — 16 folder notes named after their folder, `[[path\|alias]]` wikilinks, pipe-escaping inside tables | throughout | ✅ fully |
| **Dated-prefix filing** — `YYYY-MM-DD <Type> <Detail>`, date-of-event not date-of-upload, raw original preserved untouched | `CLAUDE.md` §Uploads | ✅ fully |
| **Living question lists per advisor**, split Urgent / Next visit / Settled | `01 Master/Questions — *.md` | ⚠️ generalizes as "Questions — \<advisor\>" |
| **Critique generation** — steelman for, strongest case against, interaction checks, contradictions between advisors | `04 Critiques/` | ⚠️ generalizes as "critique of expert advice received" |
| **Gap audit** — periodic full re-read hunting for what's missing, stale, or self-contradictory | `07 Deep Dives/Gap Analysis I & II` | ✅ fully |
| **Trend tables** — dedupe by date+marker, flag conflicting values, canonical file is source of truth | `05 Trends/` | ✅ as "longitudinal numbers" |
| Clinical domain content — lab reference ranges, doctor roles, medication timing | health-specific | ❌ preset only |

**Nothing of the maintainer's data goes into the plugin.** Templates and rules only. This is a hard build requirement, checked at packaging time.

---

## 2. Architecture — two layers

```
core (domain-neutral)          preset (domain-specific)
─────────────────────          ────────────────────────
01 Master/                     Questions — <advisor>.md ×N
  Master Summary               Results/ · Visits/
  Settled — do not re-open     Trends: lab markers, vitals
02 Chronicle/                  Critique template: clinical
  Timeline · Prompt Log        Glossary, reference ranges
03 Inbox/                      Consent-to-store-health-data step
04 Critiques/
05 Trends/
06 Reference/ (+ Raw Archive/, Snapshots/)
07 Deep Dives/
99 Archive/
CLAUDE.md engine · 00 START HERE
```

A preset is **data, not code** — a single manifest describing extra folders, extra Master files, the advisor-role vocabulary, trend-table columns, and any domain-specific rules to append to `CLAUDE.md`. Adding "eldercare" or "legal matter" later means writing one manifest, not touching the engine.

Ship v1 with two presets: **`health`** (full fidelity to this project) and **`generic`** (core only). That is enough to prove the seam is in the right place without abstracting on a sample size of one.

---

## 3. Plugin + marketplace structure

Per the [plugins reference](https://code.claude.com/docs/en/plugins-reference), components must sit at the plugin **root** — only the manifest goes in `.claude-plugin/`. Getting that wrong is the number-one cause of "my skills don't appear."

```
records-marketplace/                        ← git repo, this is the marketplace root
├── .claude-plugin/
│   └── marketplace.json
└── plugins/
    └── records-project/
        ├── .claude-plugin/
        │   └── plugin.json
        ├── skills/
        │   ├── bootstrap-records-project/SKILL.md
        │   ├── file-to-records/SKILL.md
        │   ├── records-gap-audit/SKILL.md
        │   └── records-critique/SKILL.md
        ├── templates/
        │   ├── core/          CLAUDE.md.tmpl · 00 START HERE.md.tmpl · Master Summary ·
        │   │                  Settled register · Timeline · Prompt Log · 9 folder notes
        │   └── presets/
        │       ├── health/    manifest + Questions—advisor · Results/Visits notes ·
        │       │              trend headers · clinical critique template
        │       └── generic/   manifest only
        ├── scripts/
        │   ├── scaffold.py       build tree + folder notes from core + preset
        │   ├── snapshot.py       the zip logic, incl. iCloud workarounds
        │   └── validate.py       wikilinks resolve · folder notes present · no 0-byte files
        ├── README.md
        └── LICENSE
```

`marketplace.json`:

```json
{
  "name": "records-projects",
  "owner": { "name": "the maintainer" },
  "plugins": [
    {
      "name": "records-project",
      "source": "./plugins/records-project",
      "description": "Bootstrap and run a structured personal records project — medical, legal, or general — with an Obsidian-friendly vault, a chronological chronicle, per-advisor question lists, and a settled-questions register."
    }
  ]
}
```

`plugin.json` — `name` is the only required field; everything else is metadata. Version explicitly so updates are controllable.

---

## 4. The four skills

**`bootstrap-records-project`** — *the headline.* Interviews, then builds.
Trigger phrasing must be pushy (Claude under-triggers skills): *"Use whenever someone wants to set up, organize, or start tracking a medical case, legal matter, or any ongoing personal record-keeping project — even if they don't say the word 'project'."*

Interview (asked as one batched multiple-choice round where possible, not an interrogation):

1. Whose records, and what domain → selects preset
2. Name, DOB / matter reference
3. The advisors — names + roles → generates one `Questions — <name>.md` each, pre-split Urgent / Next / Settled
4. What they want tracked longitudinally → seeds `05 Trends` headers
5. Obsidian + Folder Notes? → toggles folder-note generation and wikilink style
6. Snapshot trigger — on Master change (default) / every turn / never
7. Cloud-synced folder? → if yes, writes the iCloud/Dropbox cautions into the generated `CLAUDE.md`
8. Consent to store personal/health data in Claude's memory → gates the memory-seeding step

Then: run `scaffold.py`, write a seeded `Master Summary` from the interview answers, write `CLAUDE.md` with the chosen options baked in, generate folder notes, run `validate.py`, take snapshot zero, and announce what was built.

**`file-to-records`** — the recurring intake loop: classify Type A vs Type B, identify document type and *event* date, rename to `YYYY-MM-DD <Type> <Detail>`, file, copy the untouched original to Raw Archive, merge tabular data into Trends deduping by date+marker, add a Timeline row, update Master if the picture changed, append to Prompt Log, empty Inbox. Mostly a restatement of what the generated `CLAUDE.md` already does — its value is being invocable on demand and available when someone is working outside the project folder.

**`records-gap-audit`** — full re-read hunting for: unaddressed abnormal findings, overdue follow-ups, self-contradictions across documents, items with no named owner, stale "pending" items that were actually never done. **Must check the Settled register first and report only genuinely new gaps** — the failure mode this project actually hit, three times.

**`records-critique`** — given a recommendation from an advisor: steelman the case for, the strongest case against, interactions and contradictions with other advisors' advice, what it assumes, and what questions it raises. Ends with balanced options, never a directive.

---

## 5. ✅ PHASE 1 RESULT (run 2026-08-08) — the risk is cleared

**Bundled plugin scripts DO execute in Cowork.** The spike is built and passing at `_plugin-dev/records-marketplace/`. Findings, all verified empirically rather than assumed:

| Question | Answer |
|---|---|
| Do plugin skills reach the Cowork bash sandbox? | **Yes** — mounted read-only at `/sessions/<session>/mnt/.claude/skills/<skill-name>/` |
| Is the plugin name in that path? | **No — it's flattened by *skill* name.** `anthropic-skills:docx` lands at `.../skills/docx/`. Don't expect a plugin-name segment. |
| Can a bundled script run? | **Yes.** Executed `skill-creator/scripts/quick_validate.py` (an installed plugin's own script) and our `probe.py`, both fine. Python 3.10.12 on Linux. |
| Is `${CLAUDE_PLUGIN_ROOT}` available? | **No.** No `CLAUDE_PLUGIN_ROOT` in the sandbox environment at all — only `CLAUDE_TMPDIR`, `CLAUDE_CODE_TMPDIR` and two proxy-port vars. **Confirms the constraint; a shell command depending on it fails silently here.** |
| What locating strategy works? | **`__file__`-relative resolution, in every case.** Once Claude invokes the script by any working path, the script resolves everything else relative to itself. Verified from an unrelated `cwd`, and again after copying the whole plugin to a different filesystem (the iCloud mount) — still resolved correctly. |
| How does the *skill* find the script in the first place? | Glob the mount: `ls -d /sessions/*/mnt/.claude/skills/<skill-name>` — confirmed to resolve a real installed skill. Fall back to `${CLAUDE_PLUGIN_ROOT}` for Claude Code. |

**The resulting rule, now baked into the spike skill:** *never hardcode a plugin path in a shell command — locate the script once, then let the script self-resolve via `__file__`.*

### What else Phase 1 produced

Rather than a throwaway, the spike carries four working scripts, all passing:

- **`probe.py`** — the portability probe; prints surface, strategy, and a `RESULT:` line.
- **`lint_frontmatter.py`** — enforces the portable six-key subset. Would have caught any non-portable key before it reached Cowork.
- **`lint_privacy.py`** — the packaging gate. **It immediately caught a real leak**: "the maintainer" in the `plugin.json` author field. That prompted a genuine design fix — the gate now has **two tiers**: `CLINICAL` patterns (doctor names, medications, DOB, diagnoses) that fail *anywhere*, and `IDENTITY` patterns (your surname) allowed *only* in manifest author fields. A single-tier gate would have been either useless or unshippable.
- **`scaffold.py`** — the real core+preset builder, not a stub. Ran end to end: built a 14-folder `health` vault with 14 folder notes, Obsidian config, and `00 START HERE`.
- **`validate_vault.py`** — checked the output: 15 notes, every folder note present and correctly named, **every wikilink resolves, zero 0-byte files.**

**Phase 2 is therefore largely done** — the core scaffold, both presets, and vault validation all work. What remains for Phase 2/3 is the template *content* (the real `CLAUDE.md` engine, Settled register, Master Summary, Timeline, Prompt Log) and the interview.

### Two things learned that change the plan

1. **`obsidian-vault-seed` is the closest existing analogue, and it is instructions-only** — two frontmatter keys, no scripts, no path variables. It also documents the exact Folder Notes `data.json` settings, which we can adopt rather than rediscover. Worth reading before writing our Obsidian layer. *Caution: it references `device_bash` / `SendUserFile` / `device_commit_files`, tools that don't exist on this surface — a reminder that skills can quietly assume a surface. Ours must not.*
2. **The Folder Notes config is now captured from your live vault** (`folderNoteName: "{{folder_name}}"`, `storageLocation: insideFolder`, `hideFolderNote`, `underlineFolder`, `openFolderNoteOnClickInPath`, `syncFolderName`) and is baked into `scaffold.py --obsidian`.

---

## 5b. ⚠️ Cowork compatibility — the constraints (now confirmed)

Cowork **does** support plugins: Customize → Plugins → Personal plugins → **+** → Add marketplace (GitHub repo), then Install. Bundled skills work in Cowork, Claude Desktop chat, and web. So the target is real.

Two constraints follow, and both are easy to violate:

**① Frontmatter must use the portable six-field subset.** Outside Claude Code, only `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` are permitted — **any other key is a hard error**, not a warning. So: no `argument-hint`, no `disable-model-invocation`, no `context: fork`, no `agent`, no `model`, no `paths`. Everything the skill needs to know goes in the body prose.

**② Don't depend on `${CLAUDE_PLUGIN_ROOT}` inside shell commands.** Cowork's bash runs in a separate Linux sandbox with its own mount paths; the plugin root resolves to a host path that the sandbox may not see at the same location. In this session, skills appear at a translated `/…/mnt/.claude/skills/` path. **Design the scripts to be located and run by Claude using its file tools rather than hardcoding plugin-root paths in shell** — or keep the logic in skill instructions and let Claude write the throwaway script. *This is the biggest technical unknown and gets tested first (Phase 1), before anything else is built on top of it.*

Also worth knowing: the docs warn `${CLAUDE_PLUGIN_ROOT}` changes on every plugin update — never write state there.

---

## 6. Build phases

| Phase | Work | Done when |
|---|---|---|
| **0 — Extract & de-identify** | Pull `CLAUDE.md`, `00 START HERE`, Settled register, Timeline, Prompt Log, Master Summary and all 16 folder notes into templates. Strip every name, date, condition, doctor and lab value; replace with placeholders. Grep the result for leaked identifiers. | A reviewer can read every template and learn nothing about the maintainer |
| **1 — Spike the risk** ⚠️ | Minimal one-skill plugin. Test `claude --plugin-dir`, then install into **Cowork** from a local marketplace and confirm the skill triggers *and that a bundled script can actually be executed*. | ✅ **DONE 2026-08-08.** Scripts run; `__file__` strategy confirmed; 3 linters + scaffold + validator all passing. **Still outstanding: a real Cowork *install* from a marketplace** (a UI action — see below) |
| **2 — Core scaffold** | ~~`scaffold.py` + core templates + `generic` preset + `validate.py`~~ ✅ **scripts done in Phase 1.** Remaining: the template *content* — real `CLAUDE.md` engine, Settled register, Master Summary, Timeline, Prompt Log, de-identified. | An empty folder becomes a valid, link-clean vault ✅ *(structure verified; content pending)* |
| **3 — Interview + health preset** | ✅ **DONE 2026-08-08.** 6 de-identified core templates + `{{VAR}}`/`{{#if}}` renderer; `health` + `generic` preset manifests with the conservatism dial; per-advisor question lists; seeded trend CSVs; `bootstrap-records-project` with the batched interview and consent-gated memory. **288 combinations tested, 0 failures.** | ✅ A fresh project stands up from a single invocation |
| **4 — Companion skills** | ✅ **DONE 2026-08-08.** `file-to-records`, `records-gap-audit`, `records-critique`, plus `snapshot.py` (scratch-build + copy-verify + 0-byte exclusion). All 5 skills pass the portability linter; descriptions well under the 1,536-char listing limit; trigger-cue coverage checked. | ✅ Each carries the operating knowledge, not just the mechanics |
| **5 — Marketplace + real trial** | **NEXT.** Move out of the vault into its own public GitHub repo; `claude plugin validate --strict`; install via Cowork on a clean machine; run it for an actual second person; add `skill-creator` evals for triggering. | Someone who isn't the maintainer uses it unaided |

`skill-creator` handles phases 3–4 well — it has an eval harness (`evals.json`, `run_eval.py`) for checking that skills trigger on the right phrasings, and `improve_description.py` for tuning triggering. Worth using rather than hand-rolling, given "does it fire when it should" is the main failure mode for skills.

---

## 6b. Decisions taken 2026-08-08 (§7 resolved)

1. **Repo public.**
2. Health preset opinionation: **do not assume the user is the decision-maker** · steelmanned options not directives ✅ · limited-trust advisor framing ✅ · **conservatism on invasive procedures = a configurable dial**, not a constant.
3. **Memory seeded only on an explicit yes** in the interview.
4. **Obsidian optional** (default on for `local-fs`, off for the shared variant).
5. `file-to-records` deliberately duplicates the generated `CLAUDE.md` — confirmed.

→ A **multi-user variant** (Claude Tag in Slack + Google Drive) is specified separately in [[2026-08-08 Design addendum — multi-user variant (Slack + Google Drive)|the multi-user addendum]]. It introduces a **storage adapter** (`local-fs` | `gdrive`) and a **collaboration profile** (`solo` | `shared`) alongside the domain preset. **Ship solo first.**

## 7. Open decisions *(resolved — kept for provenance)*

1. **Repo public or private?** Public makes Cowork installation trivial and lets you hand someone a one-line instruction. Private means the marketplace URL needs credentials. Nothing in the plugin is sensitive after Phase 0, so public is defensible — but it does put your workflow design on the internet under your name.
2. **How opinionated should the health preset be?** It currently encodes real stances: *the user is the decision-maker, present steelmanned options not directives, limited-trust framing for advisors, conservative default on invasive procedures.* Those fit you. They may not fit someone who wants their doctor's advice summarized rather than interrogated. Ship as defaults, ask in the interview, or ship two health variants?
3. **Does the plugin seed Claude's memory?** Powerful, but memory is per-user and health data needs explicit consent. Proposal: interview asks, and the skill writes memory only on an explicit yes.
4. **Obsidian assumed or optional?** Folder notes are harmless if unused, so default on, with a toggle.
5. **Does `file-to-records` duplicate the generated `CLAUDE.md`?** Deliberately, yes — one for automatic behavior inside the project, one for on-demand use anywhere. Confirm that's wanted before building both.

---

## 8. Test plan

- **Structural:** `claude plugin validate ./plugins/records-project --strict` — must pass clean.
- **Portability:** frontmatter linter asserting only the six allowed keys appear in any `SKILL.md`.
- **Privacy:** grep every template for a list of known identifiers (names, DOB, doctor names, condition terms, lab values) — must return nothing. Runs at packaging.
- **Functional:** scaffold into a temp dir; assert every folder note exists and is named after its folder; assert every `[[wikilink]]` resolves; assert no 0-byte files.
- **Triggering:** `skill-creator` evals — ~10 prompts per skill, mixing phrasings that *should* fire it with near-misses that shouldn't.
- **End-to-end:** stand up a fictional patient in a scratch folder, run three turns of intake through it, confirm Timeline / Prompt Log / Trends / snapshot all update correctly.
- **Cross-surface:** confirm identical behavior in Claude Code and Cowork.

---

## 9. Effort estimate

Phases 0–2 are a session's work. Phase 3 is the real content — probably two sessions, mostly writing the health preset carefully. Phases 4–5 are iterative and can trail. **Phase 1 comes first and is non-negotiable**, because if bundled scripts can't run in Cowork, the whole design shifts to instructions-only and it's much cheaper to learn that on day one.

---

*Sources: [Plugins reference](https://code.claude.com/docs/en/plugins-reference) · [Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) · [Create plugins](https://code.claude.com/docs/en/plugins) · [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude) · [Browse skills, connectors, and plugins](https://support.claude.com/en/articles/14328846-browse-skills-connectors-and-plugins-in-one-directory)*
