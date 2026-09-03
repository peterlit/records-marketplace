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

# Folders whose notes come from a template rather than the generated stub.
TEMPLATED_FOLDERS = {"memory": "memory", "_sync": "_sync"}


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



# ---------- link style: wiki (Obsidian default) or standard markdown -------
# Templates are authored ONCE in wikilink form; markdown mode is a render-time
# conversion. That keeps a single source of truth for every template.

WIKILINK = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")


def build_link_map(folders, root_files):
    """target-as-written -> vault-relative path. Folder notes are addressable by
    their bare name ("01 Master") and by their full relative path."""
    m = {}
    for rel in folders:
        name = os.path.basename(rel)
        note = f"{rel}/{name}.md"
        m.setdefault(name, note)
        m.setdefault(rel, note)
    for rf in root_files:                       # e.g. "MEMORY.md", "00 START HERE.md"
        stem = rf[:-3] if rf.endswith(".md") else rf
        m.setdefault(stem, rf)
    return m


def to_plain_text(text):
    """Strip link syntax entirely, keeping the human-readable label.

    Google Drive's plain-text preview auto-linkifies anything that looks like a
    path, so [Conditions](Conditions/Conditions.md) becomes a clickable and
    BROKEN http://conditions/Conditions.md. Wikilinks are inert but ugly. For a
    vault read primarily in Drive, no link syntax at all is the honest answer.
    """
    def repl(m):
        target, alias = m.group(1).strip(), (m.group(2) or "").strip()
        return alias or target.split("/")[-1]
    return WIKILINK.sub(repl, text)


def to_markdown_links(text, from_dir, link_map, unresolved):
    """Rewrite [[target|alias]] as [alias](relative/path.md), URL-encoding spaces."""
    def repl(m):
        target, alias = m.group(1).strip(), (m.group(2) or "").strip()
        label = alias or target.split("/")[-1]
        dest = link_map.get(target)
        if dest is None:                        # a plain file reference like "01 Master/Master Summary"
            cand = target + ".md"
            dest = cand if cand in link_map.values() else None
        if dest is None:
            unresolved.add(target)
            return m.group(0)                   # leave as-is; validate_vault will flag it
        rel = os.path.relpath(dest, from_dir or ".")
        return f"[{label}]({rel.replace(' ', '%20')})"
    return WIKILINK.sub(repl, text)


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


def obsidian_config(target, markdown_links=False):
    od = os.path.join(target, ".obsidian", "plugins", "folder-notes")
    os.makedirs(od, exist_ok=True)
    j = lambda p, o: json.dump(o, open(p, "w", encoding="utf-8"), indent=2)
    j(os.path.join(target, ".obsidian", "community-plugins.json"), ["folder-notes"])
    j(os.path.join(target, ".obsidian", "app.json"),
      {"alwaysUpdateLinks": True, "newLinkFormat": "shortest", "useMarkdownLinks": markdown_links})
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
    ap.add_argument("--links", default="wiki", choices=["wiki", "markdown", "plain"],
                    help="wiki = [[Obsidian wikilinks]] (default; inert but bracket-y "
                         "outside Obsidian). markdown = [standard](links.md), good for "
                         "GitHub and markdown viewers - but NOT Google Drive, whose text "
                         "preview auto-linkifies relative paths into broken http:// URLs. "
                         "plain = no link syntax at all, just readable names; the right "
                         "choice when people read the vault in Drive's browser preview.")
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
    ctx["CO_USER_OTHER"] = co[1] if len(co) > 1 else "the other co-user"
    if shared:
        # In shared mode nobody is "the operator" - the engine addresses whoever is typing.
        ctx["OPERATOR_NAME"] = "either co-user"
        ctx["CO_USER_OTHER"] = co[1]

    advisors = [s.split(":", 1) if ":" in s else (s, "") for s in a.advisor]
    ctx["ADVISOR_ROSTER"] = ("\n".join(
        f"- **{n.strip()}**{' — ' + r.strip() if r.strip() else ''}" for n, r in advisors)
        or f"_No {preset['advisor_word_plural']} recorded yet._")

    # folders + folder notes
    folders = dict(CORE_FOLDERS)
    for k, v in preset["folders"].items():
        folders[k] = v

    # Link rewriting needs to know every note this run will create.
    root_files = ["00 START HERE.md", "CLAUDE.md", "MEMORY.md"]
    link_map = build_link_map(folders, root_files)
    link_map["MEMORY"] = "MEMORY.md"
    link_map["memory"] = "memory/memory.md"
    for rel in ("01 Master/Master Summary", "01 Master/Settled — do not re-open",
                "02 Chronicle/Timeline", "02 Chronicle/Prompt Log"):
        link_map[rel] = rel + ".md"
    for n, r in [s.split(":", 1) if ":" in s else (s, "") for s in a.advisor]:
        link_map[f"01 Master/Questions — {n.strip()}"] = f"01 Master/Questions — {n.strip()}.md"
    unresolved = set()
    md_links = (a.links == "markdown")

    def emit(dest_rel, text):
        """Single write path so link conversion can never be forgotten."""
        if a.links == "markdown":
            text = to_markdown_links(text, os.path.dirname(dest_rel), link_map, unresolved)
        elif a.links == "plain":
            text = to_plain_text(text)
        return write(os.path.join(a.target, dest_rel), text)

    made = 0
    for rel, desc in folders.items():
        d = os.path.join(a.target, rel); os.makedirs(d, exist_ok=True)
        kids = [os.path.basename(o) for o in folders if os.path.dirname(o) == rel]
        emit(os.path.join(rel, f"{os.path.basename(rel)}.md"),
             folder_note(rel, desc.format(advisor=preset["advisor_word"]), kids))
        made += 1

    # core templates
    for dp, _, fns in os.walk(os.path.join(TPL, "core")):
        for fn in sorted(fns):
            if not fn.endswith(".tmpl"): continue
            src = os.path.join(dp, fn)
            rel = os.path.relpath(src, os.path.join(TPL, "core"))[:-5]
            if rel.startswith("_sync") and not shared:
                continue          # presence markers are a shared-mode concept
            emit(rel, render(open(src, encoding="utf-8").read(), ctx))

    # one question list per advisor
    qt = open(os.path.join(pdir, "Questions.md.tmpl"), encoding="utf-8").read()
    for n, r in advisors:
        c = dict(ctx, ADVISOR_NAME=n.strip(), ADVISOR_ROLE=r.strip(), advisor_role=bool(r.strip()))
        emit(os.path.join("01 Master", f"Questions — {n.strip()}.md"), render(qt, c))

    # trend tables
    for fn, header in preset["trends"].items():
        p = os.path.join(a.target, "05 Trends", fn)
        if not os.path.exists(p):
            write(p, header + "\n")

    # memory/ always; _sync/ only when there is more than one co-user
    os.makedirs(os.path.join(a.target, "memory"), exist_ok=True)
    if shared:
        os.makedirs(os.path.join(a.target, "_sync"), exist_ok=True)

    if a.obsidian:
        obsidian_config(a.target, markdown_links=(a.links == "markdown"))
        if a.links == "plain":
            print("  NOTE: --links plain removes link syntax, so Obsidian navigation "
                  "and Folder Notes click-through will not work. Choose wiki if "
                  "Obsidian is the primary reader.")

    if unresolved:
        print("  WARNING unresolved link targets (left as wikilinks): "
              + ", ".join(sorted(unresolved)))
    print(f"preset={a.preset} links={a.links} folders={made} advisors={len(advisors)} "
          f"conservatism={a.conservatism} obsidian={a.obsidian} memory={a.memory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
