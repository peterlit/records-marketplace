---
name: records-chat-companion
description: Set up a claude.ai chat Project as a read-and-capture companion to an existing records project stored on Google Drive - for asking the record questions away from your computer, and capturing things that happened so they can be filed properly later. Generates paste-ready Project instructions. Use when someone wants access to their records project from their phone or the web, wants to consult it at an appointment, or asks about using it outside their computer. Only applies INSIDE an existing records project - a folder containing a CLAUDE.md and 01 Master/, or a .records-project.json marker. Do NOT use it to build a records project in a chat; it configures a companion to one that already exists.
license: MIT
---

# Chat companion for an existing records project

Produces the custom instructions for a **claude.ai Project** that reads the same Drive folder
this vault lives in. The companion answers questions and captures new events; it never curates.

## Why it may not write to the record

Cowork has `preflight.py`, `validate_vault.py`, snapshot zips and 0-byte detection. **A chat
Project has none of it**, and it is a second writer that cannot see what the first is doing.
So the companion is confined to creating files in `03 Inbox/`, which `file-to-records` then
files with the full verification path intact. This is a policy choice, not a technical limit —
the Drive connector *can* edit content (create-new → trash-old → rename). We decline to.

## Step 1 — resolve the Drive folder ids

The script cannot see Drive; the connector can. Find the vault folder and its `03 Inbox`:

```
search_files: title contains '<vault folder name>' and mimeType = 'application/vnd.google-apps.folder'
search_files: parentId = '<vault id>' and title contains 'Inbox'
```

If either is missing, the vault may not be synced to Drive yet — say so rather than guessing an id.

## Step 2 — generate

```bash
python3 <scripts>/chat_companion.py "<vault>" \
  --vault-folder-id <id> --inbox-folder-id <id>
```

It reads `.records-project.json`, so subject, operator, decision-maker, conservatism and
language all match the authoritative side automatically. Output lands in
`06 Reference/Chat companion — project instructions.md`.

## Step 3 — hand over

Tell them, in this order:

1. Create a Project on claude.ai and **paste the file's contents into its custom instructions**.
2. Connect the **Google Drive** connector in that account.
3. What it can do: answer from the record, critique a recommendation, help prepare for an
   appointment, capture what just happened.
4. What it will not do: change the Master Summary, resolve questions, merge trends, or file
   anything. Captured notes sit in `03 Inbox` marked *not yet filed* until Cowork picks them up.

## The failure that is silent

The instructions tell the companion to read with `download_file_content`, **never**
`read_file_content` — the latter does not support `text/markdown` and returns an empty string
rather than an error. A companion using it would conclude the record is blank. If someone
reports the companion "can't see anything", that is the first thing to check.
