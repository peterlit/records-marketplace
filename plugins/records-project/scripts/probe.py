#!/usr/bin/env python3
"""Phase-1 probe: prove a plugin-bundled script can locate itself and run."""
import os, sys, glob, platform

SKILL = "records-spike"

def strategies():
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        yield "env:CLAUDE_PLUGIN_ROOT", os.environ["CLAUDE_PLUGIN_ROOT"]
    yield "self:__file__", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in sorted(glob.glob(f"/sessions/*/mnt/.claude/skills/{SKILL}")):
        yield "glob:cowork-mount", p
    for p in sorted(glob.glob(os.path.expanduser(f"~/.claude/skills/{SKILL}"))):
        yield "glob:user-skills", p

def surface():
    if glob.glob("/sessions/*/mnt/.claude"):
        return "cowork-sandbox"
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return "claude-code"
    return "unknown"

def main():
    won = None
    print(f"python  : {platform.python_version()} on {platform.system()}")
    print(f"cwd     : {os.getcwd()}")
    print(f"surface : {surface()}")
    print("--- strategies ---")
    for name, path in strategies():
        ok = os.path.isdir(path)
        print(f"  {'OK  ' if ok else 'MISS'} {name:26s} {path}")
        if ok and won is None:
            won = (name, path)
    if not won:
        print("RESULT: FAIL - could not locate plugin files")
        return 1
    print(f"RESULT: OK surface={surface()} strategy={won[0]} root={won[1]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
