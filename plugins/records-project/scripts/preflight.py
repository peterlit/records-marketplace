#!/usr/bin/env python3
"""Fail fast before scaffolding. Every check here is one that has, in practice,
manifested as a command that hangs for many minutes and produces nothing.

  preflight.py TARGET [--slow-seconds 3]

Exit 0 = safe to scaffold. Non-zero = STOP and tell the person what is wrong.
Never let a bootstrap "run for 15 minutes"; a correct scaffold takes 0.03s.
"""
import os, sys, time, argparse, shutil

def slurp(path, errors="strict"):
    """Read a whole text file and close it. Bare open().read() leaks the handle and
    fills test output with ResourceWarnings, which trains people to ignore output."""
    with open(path, encoding="utf-8", errors=errors) as f:
        return f.read()


SLOW = 3.0

def timed(label, fn, slow):
    t0 = time.time(); out = fn(); dt = time.time() - t0
    if dt > slow:
        print(f"  SLOW  {label}: {dt:.1f}s — cloud provider is stalling. If this is Google "
              f"Drive or OneDrive, the folder is probably in streaming mode; turn on "
              f"'Available offline' (Drive) / 'Always keep on this device' (OneDrive).")
    return out, dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--slow-seconds", type=float, default=SLOW)
    a = ap.parse_args()
    t = a.target
    slow = a.slow_seconds

    parent = os.path.dirname(os.path.abspath(t.rstrip("/")))
    if not os.path.isdir(parent):
        print(f"FAIL parent directory does not exist: {parent}")
        print("     The folder was probably never mounted into this sandbox. Do NOT search")
        print("     the filesystem for it — ask which folder to use.")
        return 2

    try:
        timed("mkdir", lambda: os.makedirs(t, exist_ok=True), slow)
    except Exception as e:
        print(f"FAIL cannot create {t}: {e}"); return 2

    # Non-empty target: the skill must confirm before scaffolding over content.
    existing = [e for e in os.listdir(t) if not e.startswith(".")]
    if existing:
        print(f"  WARN target is NOT empty — {len(existing)} entries: "
              f"{', '.join(sorted(existing)[:6])}{' …' if len(existing) > 6 else ''}")
        print("       Confirm with the person before scaffolding into it.")

    # A canary proves you can WRITE. It says nothing about whether the files already
    # there can be READ. On a cloud-synced vault an evicted file reads as 0 bytes, and
    # the danger is not a failed read - it is a successful-looking empty one that gets
    # summarised and written back. Check before trusting any read.
    if os.path.isfile(os.path.join(t, ".records-project.json")):
        stubs, empties = [], []
        for dp, dns, fns in os.walk(t):
            dns[:] = [d for d in dns if d not in (".obsidian", ".git")]
            for fn in fns:
                fp = os.path.join(dp, fn)
                if fn.endswith(".icloud"):
                    stubs.append(os.path.relpath(fp, t))
                elif fn.endswith(".md") and os.path.getsize(fp) == 0:
                    empties.append(os.path.relpath(fp, t))
        if stubs:
            print(f"FAIL {len(stubs)} evicted file(s), e.g. {stubs[0]}")
            print("     They are cloud-only and will read as 0 bytes. Turn OFF 'Optimise Mac")
            print("     Storage' for this folder and let it re-download before doing anything.")
            return 2
        if empties:
            print(f"FAIL {len(empties)} zero-byte markdown file(s), e.g. {empties[0]}")
            print("     Either a failed write or an evicted file. Do not read or rewrite them.")
            return 2
        for known in ("CLAUDE.md", os.path.join("01 Master", "Master Summary.md")):
            kp = os.path.join(t, known)
            if os.path.isfile(kp):
                if not slurp(kp, errors="replace").strip():
                    print(f"FAIL {known} exists but reads as empty — do not trust any read "
                          f"from this vault until sync has settled.")
                    return 2
        print("  existing vault: no evicted or empty files; reads are trustworthy")

    probe = os.path.join(t, ".preflight-canary")
    payload = f"canary {time.time()}\n"
    try:
        def _w():
            with open(probe, "w", encoding="utf-8") as f:
                f.write(payload)
        _, dt = timed("write", _w, slow)
    except Exception as e:
        print(f"FAIL cannot write into {t}: {e}"); return 2

    size = os.path.getsize(probe)
    if size == 0:
        print(f"FAIL wrote {len(payload)} bytes but the file is 0 bytes on disk.")
        print("     Classic cloud-streaming failure: the write did not land. Scaffolding now")
        print("     would produce a vault of empty files that reports success.")
        os.remove(probe); return 2

    back, _ = timed("read", lambda: slurp(probe), slow)
    if back != payload:
        print("FAIL read-back does not match what was written — the sync layer is mangling "
              "content. Stop; do not scaffold."); os.remove(probe); return 2

    try:
        os.remove(probe)
    except Exception:
        print(f"  WARN could not delete {probe} — deletion protection is Cowork's, not the "
              f"provider's. Use allow_cowork_file_delete. Harmless here.")

    print(f"  preflight OK — {t} is reachable, writable, and returns what it stores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
