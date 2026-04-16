# Architecture — Travel Expense Agent

## Module Dependency Order

```
config.py       ← env vars, no internal deps
models.py       ← Pydantic v2, imports config
imap_client.py  ← Gmail IMAP singleton, imports config
classifier.py   ← loads categories.json, imports models
scanner.py      ← imports imap_client, classifier, models
mailer.py       ← imports config, models
cli.py          ← imports scanner, mailer, config, models (top of stack)
```

## Key Design Decisions

- **IMAP + SMTP via Gmail** — no OAuth required; app password stored in `.env`
- **Module-level lazy singletons** — IMAP and SMTP connections initialized once, reconnected on stale
- **`categories.json`** — all classification rules live here; zero code changes to add merchants
- **`_exclude` key in categories.json** — subject patterns that mark emails as `unknown` even when sender domain matches a known category (e.g. "Update your Uber account email")
- **HTML attachments** — Outlook-compatible; `.eml` format avoided due to rendering issues
- **`application/octet-stream` fallback** — PDFs forwarded with `octet-stream` content-type are caught by filename extension check
- **Confirmation gate** — `send` command always prompts before transmitting; never auto-sends
- **Unknown filtering** — `send` drops all `ReceiptCategory.UNKNOWN` receipts silently with a count message

## Data Flow

```
CLI (send --since DATE)
  └─ scanner.scan(since, until)
       ├─ imap_client.fetch_messages()   → list[(uid, raw_bytes)]
       ├─ email.message_from_bytes()     → Message
       ├─ _decode_header()              → decoded subject/sender
       ├─ classifier.classify()          → ReceiptCategory
       ├─ _extract_amount()             → float | None
       └─ _extract_summary()            → str | None
  └─ filter unknown category
  └─ print confirmation table
  └─ prompt y/N
  └─ scanner.fetch_raw_map()            → dict[uid, raw_bytes]
  └─ mailer.send_receipts()
       ├─ _build_body()                 → email body string
       ├─ MIMEMultipart assembly
       ├─ per receipt:
       │   ├─ _extract_html()          → .html attachment
       │   └─ _extract_binary_attachments() → .pdf / .png attachments
       └─ SMTP sendmail
```

## Classification Logic

1. `has_image_only` → `PHOTO`
2. Subject matches `_exclude.subject_patterns` → `UNKNOWN`
3. Sender domain exact/subdomain match → category
4. Subject keyword match → category
5. Fallback → `UNKNOWN`

## Known Edge Cases

- **MIME-encoded subjects** (`=?US-ASCII?Q?...?=`) — decoded via `email.header.make_header` before classification
- **`application/octet-stream` PDFs** — hotel receipts often arrive with wrong content-type; extension-based fallback catches them
- **Truncated attachments** — corrupted forwarded emails produce invalid PDFs; validate PDF magic bytes (`%PDF`) and `%%EOF` before sending if needed in future
- **CC when To == CC** — `sendmail` recipients list deduplicates automatically
