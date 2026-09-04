#!/usr/bin/env python3
"""Render paste-ready claude.ai Project instructions for an existing vault.

  chat_companion.py VAULT [--vault-folder-id ID] [--inbox-folder-id ID]

Reads .records-project.json so the companion inherits the same subject, decision-maker
and conservatism as the authoritative side. Writes into 06 Reference/.
"""
import os, sys, json, argparse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(os.path.dirname(HERE), "templates")

FRAMING = {
    "conservative": ("{who} leans conservative on invasive procedures: lead with the "
                     "watchful-waiting option and what would have to change to justify escalating."),
    "balanced": ("Present watchful waiting and intervention even-handedly, with the tradeoffs "
                 "each way. {who} decides."),
    "interventionist": ("{who} is willing to act early: give the interventional option a fair "
                        "hearing rather than defaulting to wait-and-see."),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--vault-folder-id", default="<run search_files to find it>")
    ap.add_argument("--inbox-folder-id", default="<run search_files to find it>")
    a = ap.parse_args()

    cfg_p = os.path.join(a.vault, ".records-project.json")
    if not os.path.isfile(cfg_p):
        print(f"FAIL no .records-project.json at {a.vault} — this is not a records project.")
        return 2
    cfg = json.load(open(cfg_p, encoding="utf-8"))

    if cfg.get("provider") != "gdrive":
        print(f"  WARN provider is '{cfg.get('provider')}', not gdrive. The companion relies on "
              f"the Google Drive connector; on another provider it can read nothing.")

    dm = cfg.get("decision_maker") or cfg.get("operator") or "the decision-maker"
    who = f"**{dm}**"
    framing = FRAMING.get(cfg.get("conservatism", "balanced"), FRAMING["balanced"]).format(who=who)
    if cfg.get("language", "English").lower() not in ("english", "en"):
        framing += f"\n\nWrite in {cfg['language']}, as the authoritative side does."

    tpl = open(os.path.join(TPL, "companion", "chat-companion.md.tmpl"), encoding="utf-8").read()
    out = (tpl.replace("{{TITLE}}", cfg.get("title") or f"{cfg.get('subject','')} — Records")
              .replace("{{CLOUD_PROVIDER}}", "Google Drive")
              .replace("{{OPERATOR_NAME}}", cfg.get("operator") or dm)
              .replace("{{VAULT_FOLDER_ID}}", a.vault_folder_id)
              .replace("{{INBOX_FOLDER_ID}}", a.inbox_folder_id)
              .replace("{{TODAY}}", "YYYY-MM-DD")
              .replace("{{DECISION_FRAMING}}", framing))
    assert "{{" not in out, "unrendered template syntax"

    dest_dir = os.path.join(a.vault, "06 Reference")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, "Chat companion — project instructions.md")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(out)
    if os.path.getsize(dest) == 0:
        print(f"FAIL wrote 0 bytes to {dest}"); return 2
    print(f"  wrote {os.path.getsize(dest)} bytes -> {os.path.relpath(dest, a.vault)}")
    print("  Paste its contents into the claude.ai Project's custom instructions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
