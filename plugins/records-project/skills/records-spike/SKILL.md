---
name: records-spike
description: Phase-1 portability probe for the records-project plugin. Verifies that a bundled script can be located and executed on the current surface. Use when asked to test, probe, or verify plugin script execution, or to run the records-project spike.
license: MIT
---

# Records spike — plugin portability probe

Confirms that a plugin-bundled script can be **found** and **run** on whatever surface this skill is loaded into (Claude Code, or Cowork's sandboxed Linux shell), and reports which path strategy worked.

## Why this exists

`${CLAUDE_PLUGIN_ROOT}` resolves to a **host** path. Cowork's Bash runs in a separate Linux sandbox with its own mounts, and no `CLAUDE_PLUGIN_ROOT` environment variable is set there. A skill that hardcodes the plugin root in a shell command works in Claude Code and silently fails in Cowork.

## The rule this establishes

**Never hardcode a plugin path in a shell command. Locate the script first, then run it.**

## Steps

1. Locate this skill's own directory by trying each strategy in order and stopping at the first hit:

   ```bash
   for c in "${CLAUDE_PLUGIN_ROOT:-}/scripts" \
            "${CLAUDE_SKILL_DIR:-}/../../scripts" \
            $(ls -d /sessions/*/mnt/.claude/skills/records-spike 2>/dev/null) \
            $(ls -d ~/.claude/skills/records-spike 2>/dev/null); do
     [ -d "$c" ] && echo "FOUND: $c" && break
   done
   ```

   In Cowork the third strategy is the one that fires: plugin skills mount **flattened by skill name** at `/sessions/<session>/mnt/.claude/skills/<skill-name>/`, with no plugin-name segment in the path.

2. Run the probe, which performs the same resolution in Python and reports the result:

   ```bash
   python3 <located-dir>/probe.py
   ```

3. Report to the user: which strategy resolved, whether execution succeeded, and the surface detected.

## Verification

The probe exits `0` and prints a `RESULT:` line naming the surface and strategy. A non-zero exit, or no `RESULT:` line, means bundled scripts are not usable on this surface and the plugin must fall back to instructions-only skills that ask Claude to write the code inline.
