---
name: records-migrate
description: Bring an existing records project up to the current plugin version, or adopt a hand-built folder that predates the plugin so the tools recognise it. Reports what is out of date and fixes only the generated files, never curated content. Use when a project was created by an older version, when --reconfigure or another skill refuses because there is no .records-project.json, when the validator complains about something that used to pass, or when someone asks to upgrade, migrate or update an existing project. Only applies INSIDE an existing records project - a folder containing a CLAUDE.md and 01 Master/. NEVER use it to create a project; that is bootstrap-records-project.
license: MIT
---

# Migrate a records project to the current version

Older vaults keep working — the engine is in their own `CLAUDE.md`. Migrating buys the fixes
made since: the Skills table that drives filing from the file rather than description matching,
the Language section, the onboarding START HERE, and a complete `.records-project.json` so
`--reconfigure` and the other skills stop refusing.

## Report first. Always.

```bash
python3 <scripts>/migrate.py "<vault>"
```

**This writes nothing.** Show the person the findings and let them decide. Each is marked
`[FIX]` (the tool can do it) or `[MANUAL]` (it cannot, and says why).

## The rule that makes this safe

**A missing setting means the value is UNKNOWN, and unknown is not the same as empty.** Old
configs stored only a handful of keys. Re-rendering `CLAUDE.md` without the subject writes the
placeholder *"the subject"* over the person's name — and then reports success.

`migrate.py` refuses to `--apply` while any required setting is unknown, and lists the flags it
needs. **Your job is to find those values, not to invent them.** They are recoverable:

- The old `CLAUDE.md` usually names the subject in its title and the advisors in its question
  lists — read it.
- `01 Master/Questions — <name>.md` gives you the advisor roster directly.
- Anything you cannot recover, **ask**. A guessed decision-maker or conservatism dial will read
  as fact to every future session.

Confirm what you recovered before applying. Then:

```bash
python3 <scripts>/migrate.py "<vault>" --apply \
  --subject "..." --operator "..." --decision-maker "..." \
  --advisor "Name:role" --conservatism balanced --language English \
  --snapshot master --provider gdrive
```

It snapshots first, re-renders, verifies **no curated file changed**, checks no placeholder
reached `CLAUDE.md`, and runs the validator. Any of those failing aborts with the snapshot intact.

## Hand-built folders (`--adopt`)

A folder built before the plugin existed has no `.records-project.json`, so nothing can check
it. Interview for the settings exactly as `bootstrap-records-project` does — **including who the
decision-maker is, which is not necessarily whoever is typing** — then:

```bash
python3 <scripts>/migrate.py "<vault>" --adopt --apply --subject "..." [...]
```

⚠️ **Adopting rewrites `CLAUDE.md` from the current template.** If the person has hand-edited
theirs — added rules, overrides, project-specific conventions — **those edits are lost.** Read
their `CLAUDE.md` first, tell them plainly what is in it that the template does not have, and
offer to carry those rules across by hand afterwards. For a long-running project this is usually
the most valuable thing in the folder.

## What it will not do

- Touch anything in `01 Master`, `02 Chronicle`, `03 Inbox`, `04`–`07` or `99 Archive`. It
  verifies this by comparing mtime and size before and after, and aborts if any changed.
- Refresh `00 START HERE.md` unless you pass `--refresh-start-here`, which backs up the old copy
  first. People edit that file.
- Guess a setting. Ever.
