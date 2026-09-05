#!/usr/bin/env python3
"""Build a records-project vault from core templates + a domain preset.

Self-locating via __file__ - never depends on CLAUDE_PLUGIN_ROOT, which does
not exist in the Cowork sandbox.

  python3 scaffold.py TARGET --preset health --subject "Jane Doe" \
      --advisor "Dr. Chen:cardiologist" --advisor "Dr. Okafor:PCP" \
      --decision-maker "Jane Doe" --conservatism conservative --obsidian
"""
import sys, os, re, json, argparse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "templates")

try:
    with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as _f:
        PLUGIN_VERSION = json.load(_f).get("version", "unknown")
except Exception:
    PLUGIN_VERSION = "unknown"

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
        key = m.group(1)
        # {{VAR}} raises on an unknown key but {{#if}} used ctx.get(), so a typo
        # silently deleted the block instead of failing. That shipped: {{#if SHARED}}
        # dropped the records-sync-status row from every shared project.
        if key not in ctx:
            raise KeyError(f"template condition {{{{#if {key}}}}} is not a context key")
        return m.group(2) if ctx[key] else ""
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



def _persisted(a, prov, provider, co, shared, version):
    """Everything a vault must remember to rebuild its own CLAUDE.md.

    If a field is used to render CLAUDE.md it MUST be here, or --reconfigure will
    silently replace it with a placeholder. That bug shipped once; it blanked the
    subject's name on a real project.
    """
    return {
        "plugin_version": getattr(a, "plugin_version", None) or version,
        "created": datetime.date.today().isoformat(),
        "preset": a.preset, "subject": a.subject, "dob": a.dob, "title": a.title,
        "operator": a.operator, "decision_maker": a.dm,
        "advisors": list(a.advisor), "conservatism": a.conservatism,
        "situation": a.situation, "language": a.language,
        "snapshot_trigger": a.snapshot, "provider": prov,
        "store_sensitive": a.store_sensitive, "memory": a.memory,
        "obsidian": a.obsidian, "co_users": co, "shared": shared,
        "conflict_patterns": provider["conflict_patterns"],
    }


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
    ap.add_argument("--provider", default="", choices=["", "gdrive", "dropbox",
                    "icloud", "onedrive", "local"],
                    help="storage provider; loads templates/providers/<name>.json")
    ap.add_argument("--cloud", default="", help="deprecated free-text alias for --provider")
    ap.add_argument("--obsidian", action="store_true")
    ap.add_argument("--memory", action="store_true", help="explicit consent to seed memory")
    ap.add_argument("--force", action="store_true",
                    help="DESTRUCTIVE. Scaffold even though the target already looks like a "
                         "records project. Overwrites CLAUDE.md, the Master Summary, the "
                         "settled register, every question list and every folder note with "
                         "fresh templates. Use --reconfigure instead unless you mean it.")
    ap.add_argument("--plugin-version", dest="plugin_version", default=None,
                    help="Stamp this version instead of reading .claude-plugin/plugin.json. "
                         "For bridged runs where only scripts/ and templates/ were copied.")
    ap.add_argument("--language", default="English",
                    help="Language for all PROSE in the project (Master Summary, question "
                         "lists, folder notes, and Claude's narration in future chats). "
                         "Structural folder and file names always stay English - the "
                         "scripts, the validator and the skill descriptions key off them.")
    ap.add_argument("--store-sensitive", action="store_true")
    ap.add_argument("--reconfigure", action="store_true",
                    help="Rewrite CLAUDE.md and .records-project.json for an EXISTING "
                         "vault - e.g. after moving it to a different storage provider. "
                         "Touches no content: no folder notes, no Master files, no "
                         "chronicle. Refuses to run unless .records-project.json exists, "
                         "so it can never be mistaken for a fresh scaffold over live data.")
    a = ap.parse_args()

    # A rescaffold over a live vault silently reset the Master Summary, the question
    # lists and the Timeline to templates and exited 0. The only guard was a sentence
    # in SKILL.md, and prose is not a guard. Refuse in code.
    if not a.reconfigure and not a.force:
        _marks = [m for m in (".records-project.json", "CLAUDE.md", "01 Master")
                  if os.path.exists(os.path.join(a.target, m))]
        if _marks:
            print(f"FAIL {a.target} is already a records project (found: {', '.join(_marks)}).")
            print("     Scaffolding would overwrite the Master Summary, the settled register,")
            print("     every question list and every folder note with empty templates.")
            print("     Use --reconfigure to re-render CLAUDE.md safely, or --force if you")
            print("     really do intend to destroy the existing record.")
            return 2
        if os.path.isdir(a.target):
            _other = [e for e in os.listdir(a.target) if not e.startswith(".")]
            if _other:
                print(f"  WARN {a.target} is not empty ({len(_other)} entries). Scaffolding "
                      f"alongside existing content; nothing of yours is removed.")

    # --reconfigure must not silently blank the control panel. `ctx` is derived
    # from `a` further down, so restoration has to happen HERE, before any of it.
    # Anything the caller did not name on the command line comes back from disk.
    if a.reconfigure:
        _cfg_p = os.path.join(a.target, ".records-project.json")
        if not os.path.isfile(_cfg_p):
            print(f"FAIL --reconfigure needs an existing .records-project.json at {a.target}")
            print("     Refusing: without it this cannot be distinguished from a fresh scaffold.")
            return 2
        _old = json.load(open(_cfg_p, encoding="utf-8"))
        _given = {t.split("=", 1)[0].lstrip("-").replace("-", "_")
                  for t in sys.argv[1:] if t.startswith("--")}
        # (command-line flag, argparse dest, key in .records-project.json)
        for _flag, _attr, _key in (
                ("subject", "subject", "subject"), ("dob", "dob", "dob"),
                ("title", "title", "title"), ("operator", "operator", "operator"),
                ("decision_maker", "dm", "decision_maker"),
                ("conservatism", "conservatism", "conservatism"),
                ("situation", "situation", "situation"), ("preset", "preset", "preset"),
                ("language", "language", "language"), ("snapshot", "snapshot", "snapshot_trigger"),
                ("provider", "provider", "provider"),
                ("store_sensitive", "store_sensitive", "store_sensitive"),
                ("memory", "memory", "memory"), ("obsidian", "obsidian", "obsidian"),
                ("advisor", "advisor", "advisors"), ("co_user", "co_users", "co_users")):
            if _flag in _given:
                continue
            _v = _old.get(_key)
            if _v in (None, ""):
                continue
            setattr(a, _attr, list(_v) if isinstance(_v, list) else _v)
        if "provider" not in _given:
            a.cloud = None

    # Provider profile. --cloud is the old free-text flag; map it onto a profile.
    prov = a.provider
    if not prov and a.cloud:
        c = a.cloud.lower()
        prov = ("gdrive" if "drive" in c and "one" not in c else
                "dropbox" if "dropbox" in c else
                "icloud" if "icloud" in c else
                "onedrive" if "onedrive" in c else "local")
    prov = prov or "local"
    provider = json.load(open(os.path.join(TPL, "providers", prov + ".json"), encoding="utf-8"))

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
        "CLOUD_PROVIDER": provider["display"], "CONSENT_DATE": today,
        "PROVIDER_MOUNT_CAVEAT": provider["mount_caveat"] or "_none_",
        "PROVIDER_OFFLINE": provider["offline_requirement"] or "_none_",
        "PROVIDER_DELETE_NOTE": provider["delete_note"],
        "PROVIDER_HAZARDS": ("\n".join(f"- {h}" for h in provider["hazards"])
                             or "- _none recorded for this provider._"),
        "has_dob": bool(a.dob), "obsidian": a.obsidian, "cloud_folder": prov != "local",
        "memory_off": not a.memory, "store_sensitive": a.store_sensitive,
        "gdrive": prov == "gdrive",
        "has_mount_caveat": bool(provider["mount_caveat"]),
        "LANGUAGE": a.language,
        "translated": a.language.strip().lower() not in ("english", "en"),
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

    # --reconfigure: refuse unless this is demonstrably an existing vault, then
    # carry forward everything the caller did not explicitly override.
    cfg_path = os.path.join(a.target, ".records-project.json")
    if a.reconfigure:
        if not os.path.isfile(cfg_path):
            print(f"FAIL --reconfigure needs an existing .records-project.json at {a.target}")
            print("     Refusing: without it this cannot be distinguished from a fresh scaffold.")
            return 2
        old = json.load(open(cfg_path, encoding="utf-8"))
        if a.preset == "generic" and old.get("preset"):
            a.preset = old["preset"]
            pdir = os.path.join(TPL, "presets", a.preset)
            preset = json.load(open(os.path.join(pdir, "preset.json"), encoding="utf-8"))
            ctx.update({"PRESET": a.preset,
                        "DOMAIN_WORD": preset["domain_word"],
                        "DOMAIN_LOWER": preset["domain_word"].lower(),
                        "ADVISOR_WORD": preset["advisor_word"],
                        "ADVISOR_WORD_PLURAL": preset["advisor_word_plural"],
                        "ADVISOR_WORD_TITLE": preset["advisor_word_title"],
                        "HIGH_STAKES_WORD": preset["high_stakes_word"],
                        "DISCLAIMER": preset["disclaimer"],
                        "QUESTION_LIST_INTRO": preset["question_list_intro"],
                        "CONSERVATISM_NOTE": preset["conservatism_notes"][a.conservatism]})
        if not co and old.get("co_users"):
            co = old["co_users"]; shared = len(co) >= 2
            ctx["shared"] = shared
            ctx["CO_USER_LIST"] = "\n".join(f"- **{c}**" for c in co)
            ctx["CO_USER_OTHER"] = co[1] if len(co) > 1 else "the other co-user"
            ctx["FIRST_AUTHOR"] = co[0]
            if shared:
                ctx["OPERATOR_NAME"] = "either co-user"
        if not a.obsidian and old.get("obsidian"):
            a.obsidian = True; ctx["obsidian"] = True

        eng = write(os.path.join(a.target, "CLAUDE.md"),
                    render(open(os.path.join(TPL, "core", "CLAUDE.md.tmpl"),
                                encoding="utf-8").read(), ctx))
        cfg = dict(old, **_persisted(a, prov, provider, co, shared, PLUGIN_VERSION),
                   reconfigured=today)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2); f.write("\n")
        if shared:
            os.makedirs(os.path.join(a.target, "_sync"), exist_ok=True)
            # mkdir alone left the folder note missing and the validator failing.
            for _dp, _, _fns in os.walk(os.path.join(TPL, "core", "_sync")):
                for _fn in sorted(_fns):
                    if not _fn.endswith(".tmpl"):
                        continue
                    _src = os.path.join(_dp, _fn)
                    _rel = os.path.relpath(_src, os.path.join(TPL, "core"))[:-5]
                    write(os.path.join(a.target, _rel),
                          render(open(_src, encoding="utf-8").read(), ctx))
        print(f"reconfigured: provider={old.get('provider')} -> {prov}, "
              f"preset={a.preset}, shared={shared}. "
              "CLAUDE.md and .records-project.json rewritten; no content touched.")
        return 0

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
            if rel.startswith("_sync") and not shared:
                continue          # presence markers are a shared-mode concept
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

    # memory/ always; _sync/ only when there is more than one co-user
    os.makedirs(os.path.join(a.target, "memory"), exist_ok=True)
    if shared:
        os.makedirs(os.path.join(a.target, "_sync"), exist_ok=True)

    cfg = _persisted(a, prov, provider, co, shared, PLUGIN_VERSION)
    with open(os.path.join(a.target, ".records-project.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2); f.write("\n")

    if a.obsidian:
        obsidian_config(a.target)

    print(f"preset={a.preset} folders={made} advisors={len(advisors)} "
          f"conservatism={a.conservatism} obsidian={a.obsidian} memory={a.memory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
