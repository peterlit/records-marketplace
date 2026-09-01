---
name: file-to-records
description: File a new document, test result, visit note, or piece of news into an existing records project - dating it correctly, renaming it, archiving the original, merging any numbers into the trend tables, and updating the summary, timeline and question lists. Use whenever someone drops a file into a records project's Inbox, pastes a result or a doctor's message into chat, or says something new has happened in a case being tracked. Also use when asked to process, sort, file, or catch up an Inbox.
license: MIT
---

# File something into a records project

The recurring intake loop. The project's own `CLAUDE.md` describes this too — that is deliberate, so it works both automatically inside the project and on demand from anywhere.

## First: read before writing

1. Read the project's `CLAUDE.md` — it is the control panel and may have been edited.
2. Read `01 Master/Settled — do not re-open.md`. **Nothing you file may re-open a settled question without new evidence that specifically addresses it.**
3. Read `01 Master/Master Summary.md` for current state.

## Classify the message

**Type A — new substantive content**: a result, a decision, advice from an advisor, a status change, a document. Do the whole loop below.

**Type B — a conceptual or educational question** with no new fact ("how does X work?"). **Append a Prompt Log entry and stop.** Do not touch the summary, question lists, or critiques.

When it could be either, ask — or do the Type B thing and offer the rest.

## The loop (Type A)

### 1. Archive the original first, untouched

Copy the raw file into `06 Reference/Raw Archive/…` **before** doing anything else, under a dated subfolder. Never edit anything in Raw Archive.

⚠️ **Verify the copy is larger than 0 bytes.** On cloud-synced folders, files that are cloud-only copy as 0 bytes and fail silently. If it's 0, read the file through normal file tools first to force a download, then copy again.

### 2. Identify the type and the *event* date

**The date is the date the thing happened — not the date it was uploaded, and not the report-generation date.** A lab drawn on the 17th and reported on the 29th is filed under the 17th.

If the date genuinely can't be determined from the content, **ask.** Do not guess and do not use today's date.

### 3. Check it isn't already filed

Compare against existing files by content, not filename — the same result often arrives twice under different names, or as a better scan of something already on file. If it's a duplicate or a cleaner reprint of something present:

- **Do not create a second record.** Merge any newly-legible values into the existing note.
- If a value differs between versions, **that is a finding** — report it rather than silently taking the new one, and check the Settled register before treating either as authoritative.

### 4. Rename and file

`YYYY-MM-DD <Type> <Detail>` — e.g. `2026-06-17 Lab Panel - full values`. File into the appropriate `02 Chronicle` subfolder.

### 5. Extract the content

For scanned PDFs with no text layer, or where OCR is garbled: **render the pages as images and read them.** Do not report values from a mangled text layer — this is a common source of wrong numbers.

### 6. Merge numbers into `05 Trends`

Dedupe by date + marker. ⚠️ **If a value conflicts with one already recorded, flag it — never overwrite.** The canonical trend file is the source of truth; a re-upload is *possibly-overlapping input*, not a replacement. Report any old value that changed between versions.

### 7. Update the derived records

- `02 Chronicle/Timeline.md` — one line, dated.
- `01 Master/Master Summary.md` — only if the picture actually changed.
- `01 Master/Questions — <advisor>.md` — add new questions, resolve answered ones, keep the Urgent / Next / Settled split.
- If this contains **advice from an advisor**, trigger the `records-critique` skill.
- If something was **adjudicated** — a conflict resolved, a question answered for good — **add it to the Settled register** so it stays settled.
- `02 Chronicle/Prompt Log.md` — `date · topic · one-line gist · files touched`.

### 8. Snapshot, per the project's rule

Follow whatever `CLAUDE.md` says — commonly "only when `01 Master/` changed this turn." Respect `no snapshot` / `snapshot now`.

On cloud-synced folders, build the zip in scratch with Python's `zipfile` and copy it in; the `zip` binary's rename step fails on those mounts.

### 9. Empty the Inbox and announce

Say what was filed, what changed, and what you did **not** change. If deletion is blocked (common on iCloud), say which files need removing by hand rather than retrying.

## Things that are easy to get wrong

- **Filing under the upload date.** The most common error, and it corrupts the timeline permanently.
- **Trusting a garbled OCR layer** instead of rendering the page.
- **Silently overwriting a trend value** that disagrees with the record.
- **Treating a printed value as authoritative over a curated record.** Sources contain clerical errors. Check the Settled register first.
- **Reporting a "new finding" that a later document already resolved.** Read forward before flagging.
- **Filing a decision as though the person typing made it.** Record who actually decided.
