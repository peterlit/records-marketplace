#!/usr/bin/env python3
"""Post-scaffold checks: folder notes present & correctly named, wikilinks resolve, no 0-byte files."""
import sys, os, re, glob

SYNC_CONFLICT = re.compile(
    r"\(conflicted copy[^)]*\)|conflicted copy|-conflict-|\(Case Conflict\)|"
    r"\.sync-conflict-|\(\d+\)\.md$|~HEAD|\.icloud$", re.I)

def check_sync_conflicts(root):
    """Cloud sync clients resolve simultaneous writes by DUPLICATING files.
    Two Cowork instances on one synced folder is exactly that case.
    Reconciling on top of conflicted copies silently forks the record."""
    bad = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in (".git",)]
        for fn in fns + [os.path.basename(dp)]:
            if SYNC_CONFLICT.search(fn):
                bad.append(os.path.relpath(os.path.join(dp, fn), root))
    return sorted(set(bad))

root = sys.argv[1]; fails = []
md = [p for p in glob.glob(os.path.join(root,"**","*.md"), recursive=True) if ".obsidian" not in p]
stems = {os.path.splitext(os.path.basename(p))[0] for p in md} | \
        {os.path.relpath(os.path.dirname(p), root) for p in md}
for dp,dns,fns in os.walk(root):
    if ".obsidian" in dp or dp == root: continue
    name = os.path.basename(dp)
    if not os.path.isfile(os.path.join(dp, f"{name}.md")):
        fails.append(f"missing folder note: {os.path.relpath(dp,root)}/{name}.md")
for p in md:
    if os.path.getsize(p) == 0: fails.append(f"ZERO-BYTE: {os.path.relpath(p,root)}")
    for link in re.findall(r"\[\[([^\]|]+)", open(p,encoding="utf-8").read()):
        t = link.split("/")[-1].strip()
        if t not in stems and link.strip() not in stems:
            fails.append(f"broken wikilink [[{link}]] in {os.path.relpath(p,root)}")
for c in check_sync_conflicts(root):
    fails.append(f"SYNC CONFLICT COPY: {c}  <- resolve before reconciling")
print(f"  checked {len(md)} notes")
for f in fails: print("  FAIL", f)
print("  vault valid" if not fails else f"  {len(fails)} problem(s)")
sys.exit(1 if fails else 0)
