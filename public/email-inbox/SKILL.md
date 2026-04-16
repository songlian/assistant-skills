---
name: email-inbox
description: Check Yuki's Gmail inbox via IMAP. Use this skill when asked to check email, scan for new or unread messages, list recent emails, download email attachments (recordings, PDFs, receipts, voice memos), read an email body, or mark emails as read. Triggers on: "check my email", "any new emails", "download the attachment", "read that email", "mark as read", "scan inbox", "what emails came in", "get the PDF from that email".
---

<!-- Tested 2026-04-15: `python3 scripts/imap_tool.py list --limit 3` connected successfully and returned 3 emails including uid=75 "Tech Strategy" (has attachment, 9218 KB). -->

# Email Inbox

Read and manage Yuki's Gmail inbox over IMAP. Supports listing, fetching attachments, reading bodies, and marking messages read.

## Setup

Credentials live at **`email/.env`** in the workspace root. The script loads that first, with `travel-expenses/.env` and `finance-tracker/.env` as fallbacks.

Required env vars in `email/.env`:
```
YUKI_EMAIL=yukiassistant01@gmail.com
YUKI_EMAIL_APP_PASSWORD=<app password>
```

Run from **anywhere** — the script resolves paths relative to its own location:

```bash
python3 /home/songlian/.openclaw/workspace/skills/public/email-inbox/scripts/imap_tool.py <subcommand> [options]
```

Or from the skill directory:

```bash
cd /home/songlian/.openclaw/workspace/skills/public/email-inbox
python3 scripts/imap_tool.py <subcommand> [options]
```

---

## Commands

### `list` — Scan inbox

```bash
python3 scripts/imap_tool.py list [--unread-only] [--from SENDER] [--subject KEYWORD] [--limit N]
```

**Output:** JSON array of `{uid, subject, from, date, has_attachment, size_kb}`

| Flag | Meaning |
|------|---------|
| `--unread-only` | Only show unread/unseen emails |
| `--from SENDER` | Filter by sender address or name fragment |
| `--subject KEYWORD` | Filter by subject keyword |
| `--limit N` | Max results (default: 20). Returns most recent N. |

```bash
# List 5 most recent emails
python3 scripts/imap_tool.py list --limit 5

# Unread emails from a specific sender
python3 scripts/imap_tool.py list --unread-only --from "boss@example.com"

# Emails with "receipt" in subject
python3 scripts/imap_tool.py list --subject "receipt" --limit 10
```

---

### `fetch` — Download attachments

```bash
python3 scripts/imap_tool.py fetch <uid> --output-dir /path/to/dir
```

Downloads all attachments from the email to the given directory.

**Output:** JSON `{uid, subject, attachments: [{filename, path, size_kb}]}`

```bash
python3 scripts/imap_tool.py fetch 75 --output-dir /tmp/email-attachments
```

---

### `mark-read` — Mark as read

```bash
python3 scripts/imap_tool.py mark-read <uid>
```

Sets the `\Seen` IMAP flag on the message.

**Output:** JSON `{uid, marked_read: true}`

```bash
python3 scripts/imap_tool.py mark-read 75
```

---

### `body` — Read email body

```bash
python3 scripts/imap_tool.py body <uid>
```

Prints subject, from, date, then the plain-text body (HTML is stripped if no text/plain part exists).

```bash
python3 scripts/imap_tool.py body 63
```

---

## Typical Workflow

**Check for new emails:**
```bash
# 1. List unread emails
python3 scripts/imap_tool.py list --unread-only --limit 10

# 2. Read a specific email body
python3 scripts/imap_tool.py body <uid>

# 3. Download attachments if needed
python3 scripts/imap_tool.py fetch <uid> --output-dir /tmp/attachments

# 4. Mark as read when done
python3 scripts/imap_tool.py mark-read <uid>
```

**Find and download a specific attachment:**
```bash
# Find emails with attachments matching a subject
python3 scripts/imap_tool.py list --subject "invoice" --limit 20
# → pick uid from JSON output

# Download attachments
python3 scripts/imap_tool.py fetch <uid> --output-dir ~/Downloads/invoices
```

---

## When to Use Which Command

| Scenario | Command |
|----------|---------|
| "Do I have new emails?" | `list --unread-only` |
| "What emails came in today?" | `list --limit 20` |
| "Is there an email from X?" | `list --from "X"` |
| "What does that email say?" | `body <uid>` |
| "Download the attachment" | `fetch <uid> --output-dir ...` |
| "Mark that as read" | `mark-read <uid>` |

UIDs come from the `list` command output — always use the `uid` field, not the array index.

---

## References

- [`references/imap-reference.md`](references/imap-reference.md) — Gmail IMAP details, SEARCH syntax, attachment MIME types, common pitfalls
