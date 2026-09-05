#!/usr/bin/env python3
"""Portability linter: outside Claude Code only 6 frontmatter keys are legal.
Any other key is a HARD ERROR on claude.ai / Cowork / Skills API."""
import sys, glob, os

def slurp(path, errors="strict"):
    """Read a whole text file and close it. Bare open().read() leaks the handle and
    fills test output with ResourceWarnings, which trains people to ignore output."""
    with open(path, encoding="utf-8", errors=errors) as f:
        return f.read()

ALLOWED = {"name","description","license","compatibility","metadata","allowed-tools"}
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fail = 0
for f in sorted(glob.glob(os.path.join(root,"skills","*","SKILL.md"))):
    lines = slurp(f).split("\n")
    if lines[0].strip() != "---":
        print(f"FAIL {f}: frontmatter must start on line 1"); fail = 1; continue
    end = next((i for i,l in enumerate(lines[1:],1) if l.strip()=="---"), None)
    keys, depth_ok = [], True
    for l in lines[1:end]:
        if l.strip() and not l.startswith((" ","\t","-")) and ":" in l:
            keys.append(l.split(":",1)[0].strip())
    bad = [k for k in keys if k not in ALLOWED]
    name = os.path.basename(os.path.dirname(f))
    if bad:
        print(f"FAIL {name}: non-portable key(s) {bad}"); fail = 1
    elif "description" not in keys:
        print(f"FAIL {name}: missing description"); fail = 1
    else:
        print(f"  ok  {name}: {sorted(keys)}")
sys.exit(fail)
