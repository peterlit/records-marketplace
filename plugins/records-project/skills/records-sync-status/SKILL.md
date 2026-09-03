---
name: records-sync-status
description: Check who else is working in a shared records project right now, and record the start and end of your own session. Use at the beginning of any session in a shared project, when someone asks whether a co-user is currently working, before making substantial changes to shared files, or when sync-conflict copies appear and the record may have forked. Also use when asked who worked on the project recently.
license: MIT
---

# Session presence in a shared records project

Only applies to **shared** projects — those with two or more co-users, which have a `_sync/` folder. If there is no `_sync/`, this is a solo project and there is nothing to check.

## At the start of a session

```bash
python3 <scripts>/sync_status.py "<vault>" --status
```

Then **report what it says and carry on.** Do not refuse to work because someone else is active — say so and let the person decide:

> "Ben started 12 minutes ago and hasn't stopped, so he may be working right now. I'll re-read anything in `01 Master` immediately before changing it."

Then record your own arrival:

```bash
python3 <scripts>/sync_status.py "<vault>" --start "Ann" --surface cowork \
  --intent "filing the August labs"
```

The intent line is what makes the marker useful to a human rather than just to the machine.

## At the end

```bash
python3 <scripts>/sync_status.py "<vault>" --stop "Ann"
```

## Reading the output

- **ACTIVE** — a `started` marker under 4 hours old with no matching `stopped`. Someone may genuinely be working.
- **STALE** — a `started` over 4 hours old with no `stopped`. A crashed session or a closed laptop. **Treat as ended.** Say so rather than reporting them as active.
- **nobody active** — clear.

## ⚠️ What these markers are not

**They are not a lock, and must never be described as one.**

Cloud sync takes seconds to minutes to propagate. During that window your marker is invisible to the other person and theirs to you — which is precisely the interval where a lock would matter. Two sessions can each check, each see nothing, and both start.

What they *do* give you is **awareness** (collisions become rarer and visible) and an **audit trail** (who worked when, permanently).

**Safety comes from a different rule**, in the project's `CLAUDE.md`: when you intend to change a curated file in `01 Master`, note its modification time, **re-read it immediately before writing**, and if it changed, **merge rather than overwrite** — and say in the Prompt Log that you merged. That has no race window.

## If sync-conflict copies appear

Files named `(conflicted copy)`, `(2)`, `.sync-conflict-` mean **the record has forked** — two people wrote the same file and the sync provider duplicated it instead of merging.

```bash
python3 <scripts>/validate_vault.py "<vault>"
```

It detects them and refuses to pass. **Stop and reconcile before doing anything else.** Do not file, audit or summarise on top of a forked record — everything downstream inherits the fork. Resolving means reading both versions, merging by hand, and recording in the Prompt Log what was reconciled.

## Locating the scripts

Same rule as everywhere in this plugin: **never hardcode a plugin path.** `${CLAUDE_PLUGIN_ROOT}` is not set in every environment. Resolve it first — see `bootstrap-records-project/SKILL.md` for the four-strategy locator; marketplace installs land in `.remote-plugins/<opaque-id>/`.
