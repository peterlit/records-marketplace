---
name: records-export-doc
description: Render a document from a records project as a nicely formatted Google Doc for reading or sharing - a Master Summary to take to an appointment, a question list, a critique, a gap audit. Use when someone says a markdown file looks unformatted or ugly in Google Drive, wants a readable or printable version, wants to share something with a doctor, lawyer or family member, or asks for a Google Doc of anything in the project. Only applies to projects stored on Google Drive.
license: MIT
---

# Export a project document as a Google Doc

Markdown files preview in Google Drive as unformatted plain text, which reads badly. This produces a properly formatted Google Doc from any project file, **on demand**.

## ⚠️ The exported Doc is a snapshot, never the record

The `.md` file in the vault remains the single source of truth. The Doc is a **disposable rendering** of it at a moment in time.

This matters, and the design depends on it:

- **Google Docs cannot be edited through the connector** — `update_file` handles only title and parent. So a Doc can never be kept in sync; each refresh is a *new file with a new URL*.
- **Docs are invisible to everything else.** On the Drive mount a Doc is a ~170-byte `.gdoc` pointer, not content. `grep` can't search it, Obsidian can't read it, and **`snapshot.py` would archive only the pointer** — a backup containing no data, reporting success.

So: **never store project content as Google Docs, and never edit the Doc expecting it to flow back.** If someone edits an exported Doc, those edits are lost unless someone copies them into the markdown by hand.

Say this plainly when handing over the link.

## How to export

1. **Read the source file** from the vault with the file tools — you need the real markdown, not the Drive connector's read, which returns escaped text (`\\#`, `\\[\\[`).

2. **Find the destination folder id.** Use `search_files` with `parentId = '<vault folder id>'`, or create an `_exports` folder once and reuse it. Keeping exports in their own folder stops them being mistaken for records.

3. **Create the Doc** with `create_file`:
   - `title`: `<source name> — <YYYY-MM-DD>` — the date makes it obvious the Doc is a point-in-time snapshot.
   - `contentMimeType`: `text/markdown`
   - `textContent`: the markdown you read in step 1
   - **Do NOT set `disableConversionToGoogleType`.** Omitting it is what makes Drive convert markdown into a formatted Doc — headings, bold, lists all render. *(Setting it true is how the vault keeps real `.md` files; here you want the opposite.)*

4. **Tidy the links first.** Whatever link style the vault uses, links won't resolve inside a Doc:
   - `[[Master Summary]]` → strip to plain text: `Master Summary`
   - `[Master Summary](01%20Master/Master%20Summary.md)` → keep the label, drop the target
   - Replace them with plain text rather than leaving broken references. A Doc for a doctor should read as prose.

5. **Return the `viewUrl`** and say three things: what it is, that it's a snapshot dated today, and that edits to it won't flow back.

## Good candidates

The Master Summary before an appointment · a question list to bring along · a critique or gap audit to discuss with someone · an ER one-pager. Anything a person reads rather than something Claude maintains.

## Cleaning up

Exports accumulate. They can be removed with the Drive connector's `trash_file` — which works even where `rm` is refused, because deletion protection is Cowork's and the connector bypasses it. Offer to clear old exports when there are several for the same document.
