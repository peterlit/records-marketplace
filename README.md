# records-projects

A Claude plugin marketplace containing **records-project** — a plugin for standing up
and running a structured personal records project. Built for a real medical case and
generalised; the domain-specific parts are presets.

## Install

**Claude Code**
```bash
claude plugin marketplace add <owner>/records-marketplace
claude plugin install records-project@records-projects
```

**Cowork** — Customize → Plugins → Personal plugins → **+** → Add marketplace → this repo.

**Local development**
```bash
claude --plugin-dir ./plugins/records-project
claude plugin validate ./plugins/records-project --strict
```

## What it does

Ask Claude to set up a records project. It interviews you — whose records, who the
advisors are, **who actually decides**, how conservative you want options framed,
whether to use Obsidian, whether it may store anything in memory — then builds a vault
and a `CLAUDE.md` workflow engine that keeps it current. Afterwards your only filing
job is dropping files into `03 Inbox`.

See [`plugins/records-project/README.md`](plugins/records-project/README.md) for detail.

## Repo layout

```
.claude-plugin/marketplace.json
plugins/records-project/
  .claude-plugin/plugin.json
  skills/     five skills
  scripts/    scaffold, validate, snapshot, two linters, a probe
  templates/  core templates + health and generic presets
```

## Testing

```bash
P=plugins/records-project
python3 $P/scripts/lint_frontmatter.py     # portable six-key frontmatter
python3 $P/scripts/lint_privacy.py         # no subject data may ship
python3 $P/scripts/scaffold.py /tmp/v --preset health --subject "Test" --obsidian
python3 $P/scripts/validate_vault.py /tmp/v
```

## Licence

MIT — see [LICENSE](LICENSE).
