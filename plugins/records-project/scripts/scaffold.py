#!/usr/bin/env python3
"""Build a records-project vault from core templates + a domain preset.

Self-locating via __file__ - never depends on CLAUDE_PLUGIN_ROOT, which does
not exist in the Cowork sandbox.

  python3 scaffold.py TARGET --preset health --subject "Jane Doe" \
      --advisor "Dr. Chen:cardiologist" --advisor "Dr. Okafor:PCP" \
      --decision-maker "Jane Doe" --conservatism conservative --obsidian
"""
import os, re, sys, json, argparse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "templates")

CORE_FOLDERS = {
    "01 Master":     "The always-current picture. Master Summary, the settled register, and one question list per {advisor}.",
    "02 Chronicle":  "What happened, in order. Timeline, Prompt Log, and filed source documents.",
    "03 Inbox":      "The only folder you file into. Drop anything here; Claude sorts, dates, renames and archives it.",
    "04 Critiques":  "Independent critiques of advice received - steelman for, strongest case against, contradictions.",
    "05 Trends":     "Numbers over time. Canonical tables; merge new data here, deduped by date.",
    "06 Reference":  "Background that rarely changes, plus the untouched raw archive.",
    "07 Deep Dives": "Research written on demand. Gap analyses and topic explorations.",
    "99 Archive":    "Superseded material. Kept for provenance, not for reading.",
}


# ---------- tiny template renderer: {{VAR}} and {{#if flag}}...{{/if}} ----------

# Matches an {{#if}}...{{/if}} pair whose body contains no further {{#if}},
# i.e. always the innermost. Looping it resolves arbitrary nesting.
INNERMOST_IF = re.compile(r"\{\{#if (\w+)\}\}((?:(?!\{\{#if )[\s\S])*?)\{\{/if\}\}")


def render(text, ctx):
    def block(m):
        return m.group(2) if ctx.get(m.group(1)) else ""
    for _ in range(20):
        text, n = INNERMOST_IF.subn(block, text)
        if not n:
            break
    else:
        raise ValueError("template nesting too deep or unbalanced {{#if}}")
    if "{{#if" in text or "{{/if}}" in text:
        raise ValueError("unbalanced {{#if}}/{{/if}} in template")
    def var(m):
        key = m.group(1)
        if key not in ctx:
            raise KeyError(f"template variable {{{{{key}}}}} has no value")
        return str(ctx[key])
    return re.sub(r"\{\{(\w+)\}\}", var, text)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    if os.path.getsize(path) == 0:            # the cloud-sync 0-byte hazard
        raise IOError(f"wrote 0 bytes to {path}")
    return path


def folder_note(rel, desc, children):
    name = os.path.basename(rel)
    links = "\n".join(f"- [[{c}]]" for c in sorted(children)) or "_No subfolders._"
    return (f"# {name}\n\n{desc}\n\n## In here\n\n{links}\n\n---\n"
            "*Folder note - Obsidian's Folder Notes plugin binds this to the folder itself.*\n")


def obsidian_config(target):
    od = os.path.join(target, ".obsidian", "plugins", "folder-notes")
    os.makedirs(od, exist_ok=True)
    j = lambda p, o: json.dump(o, open(p, "w", encoding="utf-8"), indent=2)
    j(os.path.join(target, ".obsidian", "community-plugins.json"), ["folder-notes"])
    j(os.path.join(target, ".obsidian", "app.json"),
      {"alwaysUpdateLinks": True, "newLinkFormat": "shortest", "useMarkdownLinks": False})
    j(os.path.join(od, "data.json"),
      {"storageLocation": "insideFolder", "folderNoteName": "{{folder_name}}",
       "newFolderNoteName": "{{folder_name}}", "folderNoteType": ".md",
       "hideFolderNote": True, "underlineFolder": True, "underlineFolderInPath": True,
       "openFolderNoteOnClickInPath": True, "syncFolderName": True,
       "enableCollapsing": False, "excludeFolders": [], "autoCreate": False})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--preset", default="generic")
    ap.add_argument("--title")
    ap.add_argument("--subject", default="the subject")
    ap.add_argument("--dob", default="")
    ap.add_argument("--operator", default="the owner")
    ap.add_argument("--co-user", dest="co_users", action="append", default=[],
                    help="repeatable. Two or more makes this a shared project "
                         "with equal co-users (no operator/contributor split).")
    ap.add_argument("--decision-maker", dest="dm", default="")
    ap.add_argument("--advisor", action="append", default=[],
                    help='repeatable "Name:role"')
    ap.add_argument("--conservatism", default="balanced",
                    choices=["conservative", "balanced", "interventionist"])
    ap.add_argument("--situation", default="_Not yet described._")
    ap.add_argument("--snapshot", default="master",
                    choices=["master", "always", "never"])
    ap.add_argument("--cloud", default="", help="iCloud|Dropbox|Google Drive|OneDrive")
    ap.add_argument("--obsidian", action="store_true")
    ap.add_argument("--memory", action="store_true", help="explicit consent to seed memory")
    ap.add_argument("--store-sensitive", action="store_true")
    a = ap.parse_args()

    pdir = os.path.join(TPL, "presets", a.preset)
    preset = json.load(open(os.path.join(pdir, "preset.json"), encoding="utf-8"))
    title = a.title or f"{a.subject} — Records"
    today = datetime.date.today().isoformat()
    dm = a.dm or a.subject

    snapshot_rule = {
        "master": "create a snapshot only when a file in `01 Master` was created or changed this turn.",
        "always": "create a snapshot on every turn that changes any file.",
        "never":  "do not create snapshots automatically.",
    }[a.snapshot]

    ctx = {
        "PROJECT_TITLE": title, "SUBJECT_NAME": a.subject, "SUBJECT_DOB": a.dob,
        "OPERATOR_NAME": a.operator, "DECISION_MAKER": dm, "TODAY": today,
        "PRESET": a.preset, "SEED_SITUATION": a.situation,
        "DOMAIN_WORD": preset["domain_word"], "DOMAIN_LOWER": preset["domain_word"].lower(),
        "ADVISOR_WORD": preset["advisor_word"],
        "AN_ADVISOR": ("an " if preset["advisor_word"][0].lower() in "aeiou" else "a ") + preset["advisor_word"], "ADVISOR_WORD_PLURAL": preset["advisor_word_plural"],
        "ADVISOR_WORD_TITLE": preset["advisor_word_title"],
        "HIGH_STAKES_WORD": preset["high_stakes_word"], "DISCLAIMER": preset["disclaimer"],
        "QUESTION_LIST_INTRO": preset["question_list_intro"],
        "CONSERVATISM": a.conservatism,
        "CONSERVATISM_NOTE": preset["conservatism_notes"][a.conservatism],
        "SNAPSHOT_RULE": snapshot_rule,
        "CLOUD_PROVIDER": a.cloud or "cloud sync", "CONSENT_DATE": today,
        "has_dob": bool(a.dob), "obsidian": a.obsidian, "cloud_folder": bool(a.cloud),
        "memory_off": not a.memory, "store_sensitive": a.store_sensitive,
        "gdrive": "drive" in a.cloud.lower(),
    }

    # Co-users are PEERS. Two or more switches the engine into shared mode.
    co = [c.strip() for c in a.co_users if c.strip()]
    shared = len(co) >= 2
    ctx["shared"] = shared
    ctx["FIRST_AUTHOR"] = co[0] if co else a.operator
    ctx["CO_USER_LIST"] = ("\n".join(f"- **{c}**" for c in co)
                           if co else "_No co-users recorded._")
    if shared:
        # In shared mode nobody is "the operator" - the engine addresses whoever is typing.
        ctx["OPERATOR_NAME"] = "either co-user"

    advisors = [s.split(":", 1) if ":" in s else (s, "") for s in a.advisor]
    ctx["ADVISOR_ROSTER"] = ("\n".join(
        f"- **{n.strip()}**{' — ' + r.strip() if r.strip() else ''}" for n, r in advisors)
        or f"_No {preset['advisor_word_plural']} recorded yet._")

    # folders + folder notes
    folders = dict(CORE_FOLDERS)
    for k, v in preset["folders"].items():
        folders[k] = v
    made = 0
    for rel, desc in folders.items():
        d = os.path.join(a.target, rel); os.makedirs(d, exist_ok=True)
        kids = [os.path.basename(o) for o in folders if os.path.dirname(o) == rel]
        write(os.path.join(d, f"{os.path.basename(rel)}.md"),
              folder_note(rel, desc.format(advisor=preset["advisor_word"]), kids))
        made += 1

    # core templates
    for dp, _, fns in os.walk(os.path.join(TPL, "core")):
        for fn in sorted(fns):
            if not fn.endswith(".tmpl"): continue
            src = os.path.join(dp, fn)
            rel = os.path.relpath(src, os.path.join(TPL, "core"))[:-5]
            write(os.path.join(a.target, rel),
                  render(open(src, encoding="utf-8").read(), ctx))

    # one question list per advisor
    qt = open(os.path.join(pdir, "Questions.md.tmpl"), encoding="utf-8").read()
    for n, r in advisors:
        c = dict(ctx, ADVISOR_NAME=n.strip(), ADVISOR_ROLE=r.strip(), advisor_role=bool(r.strip()))
        write(os.path.join(a.target, "01 Master", f"Questions — {n.strip()}.md"), render(qt, c))

    # trend tables
    for fn, header in preset["trends"].items():
        p = os.path.join(a.target, "05 Trends", fn)
        if not os.path.exists(p):
            write(p, header + "\n")

    if a.obsidian:
        obsidian_config(a.target)

    print(f"preset={a.preset} folders={made} advisors={len(advisors)} "
          f"conservatism={a.conservatism} obsidian={a.obsidian} memory={a.memory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
