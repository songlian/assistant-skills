---
name: work-meetings
description: "Full operations skill for the work-meetings project. Ingest, search, summarize, and manage meeting content in ChromaDB. Use when ingesting video or audio from Google Drive (Drive URL + collection name, download and transcribe), ingesting documents (.docx, .pdf, .pptx, .txt), summarizing meetings by date range or topic (summarize this week's meetings, summarize talent discussions from April 20th, what happened in touch_base this week), semantic search over meeting content (what did we discuss about Salesforce), or listing collections. Triggers on any mention of work-meetings collections, meeting ingestion, meeting summaries, or ChromaDB queries."
---

# Work-Meetings

Project: `/home/songlian/.openclaw/workspace/work-meetings/`
Venv: `.venv/bin/python`

---

## Triggers

Use this skill when the user:

- Shares a Google Drive URL alongside a collection name → `ingest-media`
- Says "ingest this", "download and transcribe", "add to [collection]" → `ingest-media`
- Uploads a `.docx`, `.pdf`, `.pptx`, or `.txt` file and asks to ingest it → `ingest`
- Asks to summarize meetings by date, week, or topic → `summarize`
  - e.g. "summarize this week's meetings"
  - e.g. "summarize talent discussions from April 20th"
  - e.g. "what happened in touch_base this week"
  - e.g. "give me a detailed summary of the Salesforce meeting"
- Asks what was discussed in a meeting or collection → `summarize` or `search`
- Asks to search for something across meetings → `search-all`
- Asks to list collections or what's been ingested → `list-events` or `list-docs`

---

## Ingest Media from Google Drive

```bash
cd /home/songlian/.openclaw/workspace/work-meetings
.venv/bin/python -m work_meetings ingest-media "<drive_url_or_file_id>" --collection <name>
.venv/bin/python -m work_meetings ingest-media "<url>" --collection <name> --date 2026-04-24
```

- Accepts full Drive share URL or bare file ID
- Supports `.mov`, `.mp4`, `.m4a`, `.wav`, `.aac`, `.flac`, `.mp3`, any ffmpeg format
- Pipeline: Drive download → ffmpeg audio extraction → Whisper transcription → ChromaDB ingest
- Date auto-extracted from filename (MMDDYYYY or YYYY-MM-DD patterns); use `--date` to override
- **Run in background** — transcription is slow (CPU-only, ~1 min per 5 min of audio)
- Report: filename (not UUID), transcript char count, chunk count, collection name

## Ingest Local File

```bash
.venv/bin/python -m work_meetings ingest <path> --event <collection> [--date 2026-04-24]
```

Supported: `.docx`, `.pdf`, `.pptx`, `.txt`

---

## Summarize Meetings

```bash
# This week across all collections
.venv/bin/python -m work_meetings summarize --from 2026-04-20 --to 2026-04-25

# Topic-focused (semantic search + summarize)
.venv/bin/python -m work_meetings summarize --from 2026-04-20 --topic "talent discussions"
.venv/bin/python -m work_meetings summarize --from 2026-04-20 --to 2026-04-25 --topic "contact center"

# Single day
.venv/bin/python -m work_meetings summarize --on 2026-04-24

# Specific collection(s)
.venv/bin/python -m work_meetings summarize --from 2026-04-20 --collection touch_base
.venv/bin/python -m work_meetings summarize --from 2026-04-20 --collection touch_base --collection vendors

# Custom instructions / context (overrides default prompt entirely)
.venv/bin/python -m work_meetings summarize --on 2026-04-24 --context "detailed summary with all decisions and action items"
.venv/bin/python -m work_meetings summarize --from 2026-04-20 --context "Suresh was in these meetings. Focus on board-level implications."
.venv/bin/python -m work_meetings summarize --on 2026-04-24 --topic "talent" --context "Focus on officer-level decisions and specific candidate names."
```

- At least one of `--from`, `--to`, `--on`, `--topic`, `--context` required
- `--context`: free-form instructions passed as the primary Claude prompt; overrides default depth/style decisions
- Default (no `--context`): Claude reasons about appropriate detail level based on content type
- With `--topic`: uses semantic search across collections, then summarizes matching sources
- Without `--topic`: fetches all sources in the date range and summarizes each
- Full source text sent to Claude Haiku (no truncation — uses full 200K context)
- Output grouped by date → collection → source filename
- Runs in foreground; may take a few minutes for large date ranges
- **After the command completes, synthesize the output into a clean human-readable summary and post it to the channel. Do not ask the user if they want to see it — just post it.**

---

## Search

```bash
# Within one collection
.venv/bin/python -m work_meetings search "<query>" --event <collection>

# Across all collections
.venv/bin/python -m work_meetings search-all "<query>" [--n-results 10]
```

---

## List & Inspect

```bash
# All collections with date ranges
.venv/bin/python -m work_meetings list-events

# Documents in a collection
.venv/bin/python -m work_meetings list-docs --event <collection>
```

---

## Collection Conventions

- snake_case: `touch_base`, `tech_strategy`, `vendors`, `gt_lt`, `gtlcoffsite042026`
- Created automatically on first ingest
- Date metadata stored per chunk (`date: YYYY-MM-DD`); sources without dateable filenames have `date: ""`

## Known Collections (as of 2026-04-25)

| Collection | Contents | Date Range |
|---|---|---|
| touch_base | 1:1 / touch base recordings | Apr 22–24 |
| tech_strategy | E2E Resiliency deck/transcript/talking points | Apr 24 |
| vendors | Salesforce, SAP, Monthly Software Renewal | Apr 22–24 |
| gt_lt | GT staff meetings, headcount reqs | Apr 20–24 |
| gt_talent | VP talent review | Apr 24 |
| cts_finance_tech | CTS finance tech, CILL Review, Project Aztec, Forecast Intelligence | Apr 15–23 |
| cts_payroll | CTS payroll | Apr 23 |
| cts_people_tech | People tech software spend | Apr 23–24 |
| edlc | EDLC | Apr 23 |
| gtlcoffsite042026 | April 2026 GTL offsite (papers + transcripts) | Apr 20 |
| walmartfoundation | Foundation board onboarding (PDF + recordings) | Apr 15–24 |
| wmleadershipoffsite042026 | WM Leadership Offsite | Apr 14 |
| walmart_glm | Walmart GLM April 2026 | Apr 17 |
| interviews | Nithin Sharma Tech Fellow interview | Apr 20 |
| startups | GenWeb touch base | Apr 22 |
