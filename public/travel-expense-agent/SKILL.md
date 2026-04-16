---
name: travel-expense-agent
description: Scan a Gmail inbox for travel receipts (Uber, Lyft, taxis, hotels, flights, restaurants, parking, photo receipts) and forward them as attachments to an EA or any recipient. Use when asked to send receipts, find a specific receipt, list travel expenses by date range, or forward expense attachments via email. Triggers on phrases like "send receipts", "send travel expenses", "find my hotel receipt", "forward receipts to my EA", or any request to compile and email expense documentation.
---

# Travel Expense Agent

Scans a dedicated Gmail inbox for travel receipts, classifies them by category, and emails them as attachments to a recipient (typically an EA) with the owner CC'd.

## Project Location

```
/home/songlian/.openclaw/workspace/travel-expenses/
├── travel_expenses/
│   ├── cli.py          # CLI entry: list / send / find
│   ├── config.py       # All env vars
│   ├── models.py       # Receipt, ReceiptCategory
│   ├── imap_client.py  # Gmail IMAP reader
│   ├── classifier.py   # Category rules from categories.json
│   ├── scanner.py      # Orchestrates fetch + classify + summarize
│   └── mailer.py       # SMTP sender with PDF/image attachment support
├── data/categories.json  # Extensible keyword/domain rules
└── .env                  # Credentials (never committed)
```

Venv: `travel-expenses/.venv/`

## CLI Commands

```bash
cd /home/songlian/.openclaw/workspace/travel-expenses

# List receipts (no send)
.venv/bin/python -m travel_expenses list --since 2026-03-15 [--until 2026-04-06] [--category hotel]

# Send to EA with confirmation prompt
.venv/bin/python -m travel_expenses send --since 2026-03-15 [--until 2026-04-06] [--to override@email.com] [--note "Optional note for the email body"]

# Find a specific receipt (no send)
.venv/bin/python -m travel_expenses find --query "Marriott" [--since 2026-03-01] [--category hotel]
```

## Key Behaviors

- **send** always skips `unknown` category emails (security alerts, account notices, etc.)
- **send** always prompts for confirmation before sending — never auto-sends
- **CC is mandatory** — every outbound email CCs `EXPENSE_CC_EMAIL`; this is non-negotiable
- Attachments forwarded as `.html` (Outlook-compatible) + original PDFs/images as separate files
- MIME-encoded subjects are decoded before classification
- PDF content-type may be `application/octet-stream` — filename extension is used as fallback

## Configuration (.env)

```
AI_ASSISTANT_EMAIL=your-gmail@gmail.com
AI_ASSISTANT_PASSWORD=<gmail app password>
EXPENSE_EA_EMAIL=ea@example.com             # Primary recipient
EXPENSE_CC_EMAIL=owner@example.com          # Always CC'd (owner)
EXPENSE_OWNER_NAME=Owner                    # Used in subject + signature
EXPENSE_EA_NAME=EA                          # Used in greeting
EXPENSE_SENDER_NAME=AI Assistant
EXPENSE_EMAIL_SUBJECT=Travel Receipts       # Subject line prefix
```

## Receipt Categories

Defined in `data/categories.json`. Extensible — add new domains/keywords without code changes.

| Category | Examples |
|----------|----------|
| `ride_share` | Uber, Lyft |
| `taxi` | Curb, Alto |
| `restaurant` | DoorDash, OpenTable, Grubhub |
| `hotel` | Marriott, Hilton, Hyatt, Airbnb |
| `flight` | Delta, United, Southwest, Alaska |
| `parking` | SpotHero, ParkWhiz, ParkMobile |
| `photo` | Image-only forwarded receipts |
| `unknown` | Non-receipt emails (excluded from send) |

Exclusion patterns (non-receipt emails from known domains) are in the `_exclude` key.

## Updating Configuration

When the EA changes:
```bash
# Edit .env
EXPENSE_EA_EMAIL=newea@example.com
EXPENSE_EA_NAME=NewName
```

No code changes needed.

## Email Format

**Subject:** `{EXPENSE_EMAIL_SUBJECT} — {date_range} (sent by {EXPENSE_SENDER_NAME} on behalf of {EXPENSE_OWNER_NAME})`

**Body:**
- Greeting: `Hello {EXPENSE_EA_NAME},`
- Intro: `{EXPENSE_OWNER_NAME} has asked me to send over N travel receipt(s)...`
- Optional note (via `--note`)
- Receipt summary table (date | category | amount | description)
- Signature: `{EXPENSE_SENDER_NAME} / (AI Assistant to {EXPENSE_OWNER_NAME})`

**Attachments per receipt:**
- `.html` — full email body rendered (opens in any browser/Outlook)
- `.pdf` / `.png` / `.jpg` — original attachments extracted and forwarded separately

## Adding New Receipt Categories

Edit `data/categories.json`:
```json
"parking": {
  "domains": ["spothero.com", "parkwhiz.com"],
  "keywords": ["parking receipt", "parking confirmation"]
}
```

Add exclusion patterns under `_exclude.subject_patterns` to prevent non-receipt emails from known domains being misclassified.

## Common Tasks

**Send receipts since a trip start date:**
> "Send travel receipts since March 18th"
→ `send --since 2026-03-18`

**Find a specific receipt:**
> "Find my Marriott receipt from last week"
→ `find --query "Marriott" --since 2026-03-30`

**Send with a note:**
> "Send receipts and apologize for the delay"
→ `send --since 2026-03-15 --note "Apologies for the delay in submitting these."`

**Override EA recipient for testing:**
→ `send --since 2026-03-15 --to test@example.com`

See `references/architecture.md` for module design details.
