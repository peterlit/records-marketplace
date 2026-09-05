#!/usr/bin/env python3
"""Bring an older or hand-built vault up to the current plugin version.

  migrate.py VAULT                     report only - DEFAULT, writes nothing
  migrate.py VAULT --apply             snapshot first, then fix what is fixable
  migrate.py VAULT --adopt --subject "X" --advisor "N:role" [...]   no config yet

DESIGN RULE, and it is the whole point: **curated content is never touched.**
Master Summary, the settled register, question lists, Timeline, Prompt Log, filed
results and archives are irreplaceable. This tool only ever:

  - creates files that are MISSING and generated (folder notes, _sync/_sync.md)
  - writes .records-project.json, which is pure metadata
  - re-renders CLAUDE.md, which is designed to be regenerated
  - refreshes 00 START HERE.md, but ONLY with --refresh-start-here, and it backs
    the old one up first because people do edit it

Anything it cannot do safely it reports and leaves alone. Reporting a problem you
must fix by hand beats fixing it wrongly.
"""
import os
import re
import sys
import json
import argparse
import subprocess
import datetime

def slurp(path, errors="strict"):
    """Read a whole text file and close it. Bare open().read() leaks the handle and
    fills test output with ResourceWarnings, which trains people to ignore output."""
    with open(path, encoding="utf-8", errors=errors) as f:
        return f.read()


HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)

try:
    with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as _f:
        CURRENT = json.load(_f).get("version", "unknown")
except Exception:
    CURRENT = "unknown"

# Everything a vault must record about itself. Mirrors _persisted() in scaffold.py.
REQUIRED_KEYS = ("preset", "subject", "operator", "decision_maker", "advisors",
                 "conservatism", "language", "snapshot_trigger", "provider",
                 "store_sensitive", "memory", "obsidian", "co_users", "shared")

# Curated. Never written, never rewritten, not even when they look wrong.
SACRED = ("01 Master", "02 Chronicle", "03 Inbox", "04 Critiques", "05 Trends",
          "06 Reference", "07 Deep Dives", "99 Archive")


def vparts(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0")[:3]) or (0,)


class Finding:
    def __init__(self, key, detail, fix=None, manual=None):
        self.key, self.detail, self.fix, self.manual = key, detail, fix, manual

    @property
    def fixable(self):
        return self.fix is not None


def inspect(vault, cfg):
    """Everything that differs from what the current version would build."""
    out = []
    engine_p = os.path.join(vault, "CLAUDE.md")
    engine = slurp(engine_p) if os.path.isfile(engine_p) else ""
    start_p = os.path.join(vault, "00 START HERE.md")
    start = slurp(start_p) if os.path.isfile(start_p) else ""

    if cfg is None:
        out.append(Finding(
            "config", "no .records-project.json — this vault predates self-description",
            manual="re-run with --adopt and the project's settings; nothing else can be "
                   "checked until the vault can describe itself"))
        return out

    missing = [k for k in REQUIRED_KEYS if k not in cfg]
    if missing:
        out.append(Finding("config-keys",
                           f".records-project.json is missing {len(missing)} key(s): "
                           f"{', '.join(missing)} — --reconfigure would replace them with "
                           f"placeholders", fix="rewrite-config"))

    was = cfg.get("plugin_version", "unknown")
    if vparts(was) < vparts(CURRENT):
        out.append(Finding("version", f"built by {was}; current is {CURRENT}",
                           fix="rewrite-config"))

    if engine and "records-project:file-to-records" not in engine:
        out.append(Finding("skills-table",
                           "CLAUDE.md has no Skills table — filing depends on description "
                           "matching rather than being driven by this file (0.8.0)",
                           fix="rerender-engine"))

    lang = cfg.get("language", "English")
    if lang.lower() not in ("english", "en") and "## Language" not in engine:
        out.append(Finding("language",
                           f"config says {lang} but CLAUDE.md has no Language section — "
                           f"future chats will silently revert to English (0.7.0)",
                           fix="rerender-engine"))

    if cfg.get("shared") and not os.path.isfile(os.path.join(vault, "_sync", "_sync.md")):
        out.append(Finding("sync-note",
                           "shared vault has no _sync/_sync.md folder note (0.8.1)",
                           fix="rerender-engine"))

    if start and "Setting up on your computer" not in start:
        out.append(Finding("start-here",
                           "00 START HERE.md has no onboarding section, so a second person "
                           "gets no provider setup, no first prompt (0.10.0)",
                           fix="refresh-start-here"))

    if not os.path.isfile(os.path.join(vault, ".preflight-canary")):
        pass
    else:
        out.append(Finding("canary", "a .preflight-canary was left behind",
                           manual="remove it (Cowork's deletion protection blocks scripts)"))
    return out


def load_cfg(vault):
    p = os.path.join(vault, ".records-project.json")
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def scaffold_args(cfg):
    """Reconstruct the flags that would rebuild this vault's generated files."""
    a = ["--preset", cfg.get("preset", "generic")]
    for flag, key in (("--subject", "subject"), ("--dob", "dob"), ("--title", "title"),
                      ("--operator", "operator"), ("--decision-maker", "decision_maker"),
                      ("--conservatism", "conservatism"), ("--situation", "situation"),
                      ("--language", "language"), ("--snapshot", "snapshot_trigger"),
                      ("--provider", "provider")):
        v = cfg.get(key)
        if v:
            a += [flag, str(v)]
    for adv in cfg.get("advisors") or []:
        a += ["--advisor", adv]
    for cu in cfg.get("co_users") or []:
        a += ["--co-user", cu]
    for flag, key in (("--obsidian", "obsidian"), ("--store-sensitive", "store_sensitive"),
                      ("--memory", "memory")):
        if cfg.get(key):
            a.append(flag)
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--apply", action="store_true",
                    help="Actually make the changes. Takes a snapshot first.")
    ap.add_argument("--adopt", action="store_true",
                    help="Write a .records-project.json for a hand-built vault. "
                         "Requires the settings as flags; nothing is guessed.")
    ap.add_argument("--refresh-start-here", action="store_true",
                    help="Also regenerate 00 START HERE.md, backing up the old copy. "
                         "Off by default because people edit it.")
    ap.add_argument("--no-snapshot", action="store_true",
                    help="Skip the pre-change snapshot. Not recommended.")
    # adoption inputs, same names as scaffold.py
    ap.add_argument("--preset", default="generic")
    ap.add_argument("--subject", default="")
    ap.add_argument("--dob", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--operator", default="")
    ap.add_argument("--decision-maker", dest="dm", default="")
    ap.add_argument("--advisor", action="append", default=[])
    ap.add_argument("--co-user", dest="co_users", action="append", default=[])
    ap.add_argument("--conservatism", default="balanced")
    ap.add_argument("--situation", default="")
    ap.add_argument("--language", default="English")
    ap.add_argument("--snapshot", default="master")
    ap.add_argument("--provider", default="local")
    ap.add_argument("--obsidian", action="store_true")
    ap.add_argument("--store-sensitive", action="store_true")
    ap.add_argument("--memory", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(a.vault):
        print(f"FAIL no such folder: {a.vault}")
        return 2
    if not os.path.isfile(os.path.join(a.vault, "CLAUDE.md")) and \
       not os.path.isdir(os.path.join(a.vault, "01 Master")):
        print(f"FAIL {a.vault} is not a records project (no CLAUDE.md, no 01 Master/).")
        print("     Refusing: migrating a folder that is not a vault would scatter files "
              "into it.")
        return 2

    cfg = load_cfg(a.vault)
    findings = inspect(a.vault, cfg)

    print(f"  vault: {a.vault}")
    print(f"  built by: {(cfg or {}).get('plugin_version', 'unknown — no config')}"
          f"   current: {CURRENT}")
    if not findings:
        print("  up to date — nothing to migrate")
        return 0

    print(f"\n  {len(findings)} finding(s):")
    for f in findings:
        mark = "FIX " if f.fixable else "MANUAL"
        print(f"    [{mark:6}] {f.detail}")
        if f.manual:
            print(f"              -> {f.manual}")

    if not a.apply:
        print("\n  REPORT ONLY — nothing was written.")
        print("  Re-run with --apply to fix the [FIX] items. Curated content is never")
        print("  touched: only CLAUDE.md, the config, and missing generated files.")
        return 0

    # Values given on the command line fill gaps in an old config. Without this the
    # skill has no way to supply what the old config never stored.
    supplied = {t.split("=", 1)[0].lstrip("-").replace("-", "_") for t in sys.argv[1:]
                if t.startswith("--")}
    if cfg is not None:
        for flag, key, val in (("subject", "subject", a.subject), ("dob", "dob", a.dob),
                               ("title", "title", a.title), ("operator", "operator", a.operator),
                               ("decision_maker", "decision_maker", a.dm),
                               ("conservatism", "conservatism", a.conservatism),
                               ("situation", "situation", a.situation),
                               ("language", "language", a.language),
                               ("preset", "preset", a.preset),
                               ("snapshot", "snapshot_trigger", a.snapshot),
                               ("provider", "provider", a.provider),
                               ("advisor", "advisors", a.advisor),
                               ("co_user", "co_users", a.co_users),
                               ("obsidian", "obsidian", a.obsidian),
                               ("store_sensitive", "store_sensitive", a.store_sensitive),
                               ("memory", "memory", a.memory)):
            if flag in supplied:
                cfg[key] = val
        if "co_user" in supplied:
            cfg["shared"] = len(a.co_users) >= 2

        # THE RULE: a missing key means the value is UNKNOWN. Re-rendering with an
        # unknown subject writes the placeholder "the subject" over the person's name
        # and reports success. Refuse instead. (Caught by testing --apply on a
        # simulated 0.4.0 vault; it blanked the name and printed "vault valid".)
        still = [k for k in REQUIRED_KEYS if k not in cfg or cfg[k] in (None, "")]
        still = [k for k in still if k not in ("store_sensitive", "memory", "obsidian",
                                               "co_users", "shared", "situation")]
        if still and a.apply:
            print(f"\nFAIL cannot --apply: {len(still)} setting(s) are unknown and would be "
                  f"written as placeholders.")
            for k in still:
                print(f"      --{k.replace('_', '-')}")
            print("     Supply them on the command line. Nothing is guessed: an invented")
            print("     subject or advisor would propagate into CLAUDE.md and read as fact.")
            return 2

    if cfg is None and not a.adopt:
        print("\nFAIL cannot --apply without a config. Re-run with --adopt plus the "
              "project's settings.")
        return 2

    if cfg is None:
        if not a.subject:
            print("\nFAIL --adopt needs at least --subject. Nothing is guessed; a wrong "
                  "subject would propagate into CLAUDE.md.")
            return 2
        cfg = {"preset": a.preset, "subject": a.subject, "dob": a.dob, "title": a.title,
               "operator": a.operator or a.dm, "decision_maker": a.dm,
               "advisors": a.advisor, "conservatism": a.conservatism,
               "situation": a.situation, "language": a.language,
               "snapshot_trigger": a.snapshot, "provider": a.provider,
               "store_sensitive": a.store_sensitive, "memory": a.memory,
               "obsidian": a.obsidian, "co_users": a.co_users,
               "shared": len(a.co_users) >= 2}
        # --reconfigure refuses without a config on disk, so adoption has to write
        # one before re-rendering. Deliberately minimal: scaffold.py fills the rest.
        with open(os.path.join(a.vault, ".records-project.json"), "w", encoding="utf-8") as f:
            json.dump(dict(cfg, plugin_version=CURRENT,
                           created=datetime.date.today().isoformat()), f, indent=2)
            f.write("\n")
        print("    wrote .records-project.json — the vault can now describe itself")

    if not a.no_snapshot:
        print("\n  snapshot before changing anything...")
        r = subprocess.run([sys.executable, os.path.join(HERE, "snapshot.py"), a.vault],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("FAIL snapshot failed; refusing to migrate without a backup.")
            print(r.stdout + r.stderr)
            return 2
        print("   ", (r.stdout.strip().splitlines() or ["done"])[-1])

    before = {}
    for d in SACRED:
        p = os.path.join(a.vault, d)
        if os.path.isdir(p):
            for dp, _, fns in os.walk(p):
                for fn in fns:
                    fp = os.path.join(dp, fn)
                    before[fp] = os.path.getmtime(fp), os.path.getsize(fp)

    if a.refresh_start_here:
        sp = os.path.join(a.vault, "00 START HERE.md")
        if os.path.isfile(sp):
            stamp = datetime.date.today().isoformat()
            bak = os.path.join(a.vault, f"00 START HERE.md.bak-{stamp}")
            with open(sp, encoding="utf-8") as src, open(bak, "w", encoding="utf-8") as dst:
                dst.write(src.read())
            print(f"    backed up 00 START HERE.md -> {os.path.basename(bak)}")
            os.remove(sp)

    print("  re-rendering generated files...")
    r = subprocess.run([sys.executable, os.path.join(HERE, "scaffold.py"), a.vault,
                        "--reconfigure", *scaffold_args(cfg)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL re-render failed. The snapshot above has your vault as it was.")
        print(r.stdout + r.stderr)
        return 2

    changed = [p for p, sig in before.items()
               if not os.path.exists(p) or (os.path.getmtime(p), os.path.getsize(p)) != sig]
    if changed:
        print(f"\nFAIL migration modified {len(changed)} curated file(s) — this must never "
              f"happen. Restore from the snapshot.")
        for p in changed[:5]:
            print(f"      {os.path.relpath(p, a.vault)}")
        return 2
    print(f"    curated content verified untouched ({len(before)} files)")

    engine_now = slurp(os.path.join(a.vault, "CLAUDE.md"))
    for ph in ("the subject", "the owner", "_No advisors recorded yet._"):
        if ph in engine_now:
            print(f"\nFAIL CLAUDE.md now contains the placeholder {ph!r} — a real value was "
                  f"lost. Restore from the snapshot above.")
            return 2

    r = subprocess.run([sys.executable, os.path.join(HERE, "validate_vault.py"), a.vault],
                       capture_output=True, text=True)
    print("   ", (r.stdout.strip().splitlines() or [""])[-1])
    if r.returncode != 0:
        print(r.stdout + r.stderr)
        return 2
    print(f"\n  migrated to {CURRENT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
