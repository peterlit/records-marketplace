#!/usr/bin/env python3
"""Packaging gate - no subject data may ship in the plugin.

Patterns live OUTSIDE this file, in `.privacy-patterns` at the repo root, which
is gitignored. That file names real people, conditions and identifiers, so it
must never be committed - an earlier version of this script hardcoded them and
would have published the very data it exists to protect.

Copy `.privacy-patterns.example` to `.privacy-patterns` and fill it in.

Two tiers:
  CLINICAL - subject data. Never allowed anywhere.
  IDENTITY - the author's own name. Allowed only in manifests, licence, readme.

Fails closed: a missing or empty patterns file is an error, not a pass.

  python3 lint_privacy.py [--patterns PATH] [--root PATH]
"""
import sys, os, re, argparse

def slurp(path, errors="strict"):
    """Read a whole text file and close it. Bare open().read() leaks the handle and
    fills test output with ResourceWarnings, which trains people to ignore output."""
    with open(path, encoding="utf-8", errors=errors) as f:
        return f.read()


IDENTITY_OK = {".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
               "plugin.json", "marketplace.json",
               "LICENSE", "LICENSE.txt", "CHANGELOG.md", "README.md"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
SELF = os.path.basename(os.path.abspath(__file__))


def find_root(start):
    d = start
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".claude-plugin")) and \
           os.path.isdir(os.path.join(d, "plugins")):
            return d
        d = os.path.dirname(d)
    return start


def load_patterns(path):
    """`.privacy-patterns` format: `tier: regex`, one per line. # comments ok."""
    if not os.path.isfile(path):
        return None, f"patterns file not found: {path}"
    clinical, identity = [], []
    for i, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            return None, f"{path}:{i}: expected `tier: regex`"
        tier, pat = (x.strip() for x in line.split(":", 1))
        t = tier.lower()
        if t == "clinical":
            clinical.append(pat)
        elif t == "identity":
            identity.append(pat)
        else:
            return None, f"{path}:{i}: unknown tier {tier!r} (use clinical or identity)"
        try:
            re.compile(pat)
        except re.error as e:
            return None, f"{path}:{i}: bad regex {pat!r}: {e}"
    if not clinical and not identity:
        return None, f"{path}: no patterns defined"
    return (clinical, identity), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="")
    ap.add_argument("--patterns", default="")
    a = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(a.root) if a.root else find_root(here)
    patterns_path = a.patterns or os.path.join(root, ".privacy-patterns")

    loaded, err = load_patterns(patterns_path)
    if err:
        print(f"FAIL {err}")
        print("     Copy .privacy-patterns.example to .privacy-patterns and fill it in.")
        print("     Refusing to pass without patterns - this gate fails closed.")
        return 2

    clinical, identity = loaded
    c_pat = re.compile("|".join(clinical), re.I) if clinical else None
    i_pat = re.compile("|".join(identity), re.I) if identity else None

    scanned = fails = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if fn == SELF or fn.endswith(".pyc") or fn == os.path.basename(patterns_path):
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            try:
                txt = slurp(p)
            except (UnicodeDecodeError, OSError):
                continue
            scanned += 1
            for n, line in enumerate(txt.split("\n"), 1):
                if c_pat and (m := c_pat.search(line)):
                    print(f"  FAIL [clinical] {rel}:{n}: {m.group(0)!r}")
                    fails += 1
                if i_pat and (m := i_pat.search(line)) and \
                        os.path.basename(rel) not in IDENTITY_OK and rel not in IDENTITY_OK:
                    print(f"  FAIL [identity]  {rel}:{n}: {m.group(0)!r} outside manifest/licence")
                    fails += 1

    print(f"  scanned {scanned} files against "
          f"{len(clinical)} clinical + {len(identity)} identity patterns")
    print("  clean - no subject data in the plugin" if not fails
          else f"  {fails} violation(s) - DO NOT PUSH")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
