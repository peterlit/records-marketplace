#!/usr/bin/env python3
"""Presence markers for a shared records project.

Markers are creation-only files with globally unique names, so two sessions
writing at once can never collide. They provide AWARENESS and an AUDIT TRAIL.

They are NOT a lock: cloud sync takes seconds to minutes to propagate, so a
marker can be invisible to the other party over exactly the window where a lock
would matter. Safety comes from re-reading a curated file immediately before
writing it (see CLAUDE.md), not from these.

  sync_status.py VAULT --status
  sync_status.py VAULT --start "who" [--intent "..."] [--surface cowork]
  sync_status.py VAULT --stop  "who"
"""
import os, sys, glob, argparse, datetime

STALE_HOURS = 4
FMT = "%Y-%m-%dT%H-%M-%SZ"


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def sync_dir(vault):
    d = os.path.join(vault, "_sync")
    os.makedirs(d, exist_ok=True)
    return d


def parse(name):
    """<ISO>__<who>__<started|stopped>.md -> (dt, who, kind) or None."""
    base = name[:-3] if name.endswith(".md") else name
    parts = base.split("__")
    if len(parts) != 3:
        return None
    try:
        dt = datetime.datetime.strptime(parts[0], FMT).replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None
    if parts[2] not in ("started", "stopped"):
        return None
    return dt, parts[1], parts[2]


def read_markers(vault):
    out = []
    for f in sorted(glob.glob(os.path.join(sync_dir(vault), "*.md"))):
        p = parse(os.path.basename(f))
        if p:
            out.append(p)
    return out


def sessions(vault):
    """-> {who: {'active':bool,'since':dt,'stale':bool}} using the latest marker per person."""
    # Tie-break matters: a start and its stop can land in the same second, and
    # "started" would otherwise win the comparison and report a finished session
    # as still active. Rank stopped after started at equal timestamps.
    RANK = {"started": 0, "stopped": 1}
    latest = {}
    for dt, who, kind in read_markers(vault):
        key = (dt, RANK[kind])
        if who not in latest or key > latest[who][0]:
            latest[who] = (key, kind)
    out = {}
    for who, ((dt, _rank), kind) in latest.items():
        age_h = (now() - dt).total_seconds() / 3600
        out[who] = {"active": kind == "started" and age_h < STALE_HOURS,
                    "stale": kind == "started" and age_h >= STALE_HOURS,
                    "since": dt, "age_hours": age_h, "kind": kind}
    return out


def write_marker(vault, who, kind, intent="", surface=""):
    name = f"{now().strftime(FMT)}__{who}__{kind}.md"
    path = os.path.join(sync_dir(vault), name)
    body = f"who: {who}\nkind: {kind}\nutc: {now().isoformat()}\n"
    if surface: body += f"surface: {surface}\n"
    if intent:  body += f"intent: {intent}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    if os.path.getsize(path) == 0:
        raise IOError(f"wrote 0 bytes to {path}")
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--start", metavar="WHO")
    ap.add_argument("--stop", metavar="WHO")
    ap.add_argument("--intent", default="")
    ap.add_argument("--surface", default="")
    a = ap.parse_args()

    if not os.path.isdir(a.vault):
        print(f"FAIL no such vault: {a.vault}"); return 2

    if a.start:
        print("  marker:", write_marker(a.vault, a.start, "started", a.intent, a.surface))
    if a.stop:
        print("  marker:", write_marker(a.vault, a.stop, "stopped", a.intent, a.surface))

    if a.status or not (a.start or a.stop):
        s = sessions(a.vault)
        if not s:
            print("  no session markers yet"); return 0
        active = [(w, v) for w, v in s.items() if v["active"]]
        stale  = [(w, v) for w, v in s.items() if v["stale"]]
        for w, v in sorted(active, key=lambda x: x[1]["since"]):
            mins = int(v["age_hours"] * 60)
            print(f"  ACTIVE  {w}: started {mins} min ago — they may be working right now")
        for w, v in sorted(stale, key=lambda x: x[1]["since"]):
            print(f"  STALE   {w}: started {v['age_hours']:.1f}h ago, never stopped "
                  f"(>{STALE_HOURS}h) — treat as ended, not active")
        if not active and not stale:
            print("  nobody active")
        print("  NOTE: markers are awareness, not a lock. Re-read before rewriting 01 Master.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
