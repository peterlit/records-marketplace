# records-project

Bootstrap and run a structured personal records project — a medical case, a legal
matter, or any situation that accumulates documents, advisors and decisions.

## What it builds

An Obsidian-friendly vault with a Master Summary, a chronological chronicle, one
living question list per advisor, a settled-questions register, and a `CLAUDE.md`
workflow engine that keeps all of it current. After setup the only filing job is
dropping files into `03 Inbox`.

## Install

```bash
claude plugin marketplace add ./records-marketplace
claude plugin install records-project@records-projects
```

Or, in Cowork: Customize → Plugins → Personal plugins → **+** → Add marketplace.

## Use

Ask Claude to set up a records project. It interviews you, then builds and validates.

## Skills

| Skill | Fires when |
|---|---|
| `bootstrap-records-project` | Someone wants to set up, organize, or start tracking a case |
| `file-to-records` | Something new arrives — a result, a document, news from an advisor |
| `records-gap-audit` | "What am I missing?" — a full re-read hunting for what's unaddressed |
| `records-critique` | An advisor recommended something and it needs a two-sided look |
| `records-spike` | Diagnostic: verifies bundled scripts can run on this surface |

## Presets

- **health** — doctors, Results/Visits, lab and vitals trend tables
- **generic** — advisors, Records/Meetings, a single tracking table

## Scripts

| Script | Purpose |
|---|---|
| `scaffold.py` | Build the vault from core templates + a preset |
| `validate_vault.py` | Folder notes, wikilinks, 0-byte files, sync-conflict copies |
| `lint_frontmatter.py` | Enforce the portable six-key SKILL.md frontmatter subset |
| `lint_privacy.py` | Packaging gate — no subject data may ship |
| `snapshot.py` | Dated zip, built in scratch then copied (cloud-mount safe) |
| `probe.py` | Surface/portability probe |

## Design notes

- **Never hardcode a plugin path in shell.** `${CLAUDE_PLUGIN_ROOT}` does not exist
  in every environment. Locate the script, then let it self-resolve via `__file__`.
- **Frontmatter uses only** `name`, `description`, `license`, `compatibility`,
  `metadata`, `allowed-tools`. Any other key is a hard error outside Claude Code.
- **Memory is a convenience, never a source of truth.** Anything that must stay
  true across chats goes in a file.
- **Check the Settled register before "correcting" the record.** A value printed
  on a source document does not automatically outrank a curated record.
- **Cloud-synced folders:** build zips in scratch and copy in (the `zip` binary's
  rename fails), verify nothing copied as 0 bytes, expect deletion to be blocked.
