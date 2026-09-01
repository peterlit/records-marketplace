#!/usr/bin/env python3
"""Dated zip snapshot of a records project.

Built with Python's zipfile in a scratch directory and then copied in, because
the `zip` binary's rename step fails on cloud-synced mounts (iCloud, and others
that present a virtual filesystem). Verifies the copy is non-empty, because
cloud-only files copy as 0 bytes and fail silently.

  python3 snapshot.py TARGET [--out SUBDIR] [--reason "..."] [--dry-run]
"""
import os, sys, zipfile, datetime, shutil, tempfile, argparse

EXCLUDE_DIRS = {"__pycache__", ".git", ".obsidian", "node_modules"}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}
# Excluded by default: the snapshot store itself, the inbox, the archive,
# and bulky raw data. Overridable with --include-raw.
DEFAULT_EXCLUDE_RELS = [
    "06 Reference/Raw Archive/Snapshots",
    "06 Reference/Raw Archive/Test Results",
    "03 Inbox",
    "99 Archive",
]


def find_snapshot_dir(target, out):
    if out:
        return os.path.join(target, out)
    for c in ("06 Reference/Raw Archive/Snapshots", "06 Reference/Snapshots", "Snapshots"):
        if os.path.isdir(os.path.join(target, c)):
            return os.path.join(target, c)
    d = os.path.join(target, "06 Reference", "Raw Archive", "Snapshots")
    os.makedirs(d, exist_ok=True)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--out", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--include-raw", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    target = os.path.abspath(a.target)
    if not os.path.isdir(target):
        print(f"FAIL no such folder: {target}"); return 1

    excl = [] if a.include_raw else [os.path.join(target, r) for r in DEFAULT_EXCLUDE_RELS]
    snapdir = find_snapshot_dir(target, a.out)
    excl.append(snapdir)

    files, skipped_zero = [], []
    for dp, dns, fns in os.walk(target):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS]
        if any(os.path.abspath(dp).startswith(e) for e in excl):
            dns[:] = []; continue
        for fn in fns:
            if fn in EXCLUDE_NAMES or fn.endswith(".pyc"):
                continue
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) == 0:
                    skipped_zero.append(os.path.relpath(p, target)); continue
            except OSError:
                continue
            files.append(p)

    ts = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    name = f"snapshot-{ts}.zip"

    if a.dry_run:
        print(f"DRY RUN {name}: {len(files)} files")
        for z in skipped_zero:
            print(f"  WARN 0-byte, excluded: {z}")
        return 0

    # Build in scratch - never directly on the synced mount.
    tmp = tempfile.mkdtemp()
    scratch = os.path.join(tmp, name)
    with zipfile.ZipFile(scratch, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, os.path.relpath(p, target))
    built = os.path.getsize(scratch)

    dest = os.path.join(snapdir, name)
    shutil.copyfile(scratch, dest)
    shutil.rmtree(tmp, ignore_errors=True)

    got = os.path.getsize(dest) if os.path.exists(dest) else 0
    if got == 0 or got != built:
        print(f"FAIL copy verification: built {built} bytes, landed {got}")
        return 1

    print(f"snapshot {name}: {len(files)} files, {got:,} bytes -> "
          f"{os.path.relpath(dest, target)}")
    if a.reason:
        print(f"  reason: {a.reason}")
    for z in skipped_zero:
        print(f"  WARN 0-byte file excluded (cloud-only?): {z}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
