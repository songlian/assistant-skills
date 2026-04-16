# IMAP Reference — Gmail

Quick reference for the `imap_tool.py` script and Gmail IMAP behaviour.

---

## Connection

| Setting | Value |
|---------|-------|
| Host | `imap.gmail.com` |
| Port | `993` |
| Security | SSL (use `imaplib.IMAP4_SSL`) |
| Auth | Gmail app password (not account password) — requires 2FA enabled |

```python
conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
conn.login(email, app_password)
conn.select("INBOX")
```

App passwords: Google Account → Security → 2-Step Verification → App passwords.

---

## UIDs vs Sequence Numbers

**Always use UIDs.** Sequence numbers change when messages are deleted or the
mailbox is modified; UIDs are stable for the lifetime of the message.

```python
# UID-based commands — always prefer these
conn.uid("SEARCH", None, "UNSEEN")
conn.uid("FETCH", uid, "(RFC822)")
conn.uid("STORE", uid, "+FLAGS", "\\Seen")
```

Never mix UID and sequence-number calls on the same message.

---

## SEARCH Criteria Syntax

IMAP SEARCH criteria are space-separated tokens. Multiple tokens are implicitly
AND-ed. Wrap in parentheses when combining with OR.

| Criterion | Meaning |
|-----------|---------|
| `ALL` | All messages |
| `UNSEEN` | Unread messages |
| `SEEN` | Read messages |
| `FROM "addr"` | Sender contains addr |
| `TO "addr"` | Recipient contains addr |
| `SUBJECT "kw"` | Subject contains kw |
| `SINCE "DD-Mon-YYYY"` | On or after date |
| `BEFORE "DD-Mon-YYYY"` | Before date (exclusive) |
| `ON "DD-Mon-YYYY"` | On exact date |
| `LARGER N` | Message size > N bytes |
| `SMALLER N` | Message size < N bytes |

**Date format:** `DD-Mon-YYYY` e.g. `"15-Apr-2026"` — three-letter month, always.

```python
# Unread from a specific sender since April 1
criteria = '(UNSEEN FROM "boss@example.com" SINCE "01-Apr-2026")'
status, data = conn.uid("SEARCH", None, criteria)
uids = data[0].split()  # list[bytes] of UID strings
```

---

## Fetching Messages

```python
# Full message (use for body + attachments)
status, data = conn.uid("FETCH", uid, "(RFC822)")
raw_bytes = data[0][1]
msg = email.message_from_bytes(raw_bytes)

# Headers only (fast — avoids pulling large payloads)
status, data = conn.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")

# Size and flags without downloading body
status, data = conn.uid("FETCH", uid, "(RFC822.SIZE FLAGS BODYSTRUCTURE)")
```

`BODY.PEEK` does **not** set the `\\Seen` flag — use it for read-without-marking.

---

## Marking Messages

```python
# Mark as read (set \\Seen flag)
conn.uid("STORE", uid, "+FLAGS", "\\Seen")

# Mark as unread
conn.uid("STORE", uid, "-FLAGS", "\\Seen")

# Flag (star) a message
conn.uid("STORE", uid, "+FLAGS", "\\Flagged")
```

---

## Attachment MIME Types

Gmail delivers attachments with a variety of content types. Watch for:

| Type | Notes |
|------|-------|
| `application/pdf` | PDFs — most common for receipts |
| `application/octet-stream` | Generic binary — check filename extension as fallback |
| `audio/*` | Voice memos, recordings (`audio/mpeg`, `audio/mp4`, `audio/wav`) |
| `image/jpeg`, `image/png` | Photo attachments (may also be inline) |
| `application/zip` | Compressed archives |
| `application/msword` / `application/vnd.openxmlformats...` | Word/Excel docs |

**Fallback rule:** if `content_type == "application/octet-stream"` and the part
has a `.pdf` / `.mp3` filename, treat it as that type.

**Inline images** have `Content-Disposition: inline` — skip these unless explicitly
collecting images (they are usually embedded in HTML signatures).

---

## Multipart Traversal

```python
for part in msg.walk():
    ctype = part.get_content_type()
    disposition = part.get_content_disposition() or ""
    filename = part.get_filename()

    if "attachment" in disposition and filename:
        payload = part.get_payload(decode=True)  # returns bytes
        # write to disk...
```

`msg.walk()` recurses into `multipart/mixed`, `multipart/related`,
`multipart/alternative` — no manual recursion needed.

`part.get_payload(decode=True)` handles `base64` / `quoted-printable` decoding
automatically and always returns `bytes`.

---

## Header Decoding

Email headers may be RFC2047-encoded (e.g. `=?UTF-8?B?...?=`).
Always decode before use:

```python
import email.header

def decode_header(raw: str | None) -> str:
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)
```

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Using sequence numbers instead of UIDs | Always call `conn.uid(...)` not `conn.search(...)` |
| Forgetting `BODY.PEEK` sets \\Seen | Use `BODY.PEEK` for non-marking reads |
| Date format wrong in SEARCH | Must be `DD-Mon-YYYY` — month is 3-letter abbreviation |
| Attachment payload is `None` | `get_payload(decode=True)` returns `None` on empty parts — guard with `if isinstance(payload, bytes)` |
| Encoding errors in subject/from | Always `decode_header()` — raw header can be RFC2047 |
| Connection drops on long operations | Use a `noop()` health-check before each operation; reconnect on `IMAP4.abort` |
| PDF arrives as `octet-stream` | Check filename extension as content-type fallback |
| Inline images picked up as attachments | Check `Content-Disposition` — skip `inline` unless collecting images |
| Large mailbox, slow SEARCH | Use `SINCE` to constrain date range; avoid `ALL` on busy inboxes |

---

## BODYSTRUCTURE Quick Reference

`BODYSTRUCTURE` returns a nested S-expression describing the MIME tree without
downloading the body. Useful for detecting attachments cheaply:

```python
status, data = conn.uid("FETCH", uid, "(BODYSTRUCTURE)")
bs = data[0].decode("utf-8", errors="replace")
has_attachment = "attachment" in bs.lower()
```

Not fully reliable for all clients, but good as a fast pre-check.
