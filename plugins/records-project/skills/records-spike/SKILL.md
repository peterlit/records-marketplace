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
# Resolve the plugin root. Order matters; stop at the first hit.
SKILL=records-spike
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

   **Two different Cowork layouts exist.** A *marketplace-installed* plugin mounts at `/sessions/<session>/mnt/.remote-plugins/<opaque-id>/` (the id is not the plugin name); a *built-in* plugin's skills mount flattened by skill name at `/sessions/<session>/mnt/.claude/skills/<skill-name>/`. The locator must try both.

2. Run the probe, which performs the same resolution in Python and reports the result:

   ```bash
   python3 <located-dir>/probe.py
   ```

3. Report to the user: which strategy resolved, whether execution succeeded, and the surface detected.

## Verification

The probe exits `0` and prints a `RESULT:` line naming the surface and strategy. A non-zero exit, or no `RESULT:` line, means bundled scripts are not usable on this surface and the plugin must fall back to instructions-only skills that ask Claude to write the code inline.
