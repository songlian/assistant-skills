"""Gmail IMAP tool — standalone CLI for listing, fetching, and managing emails.

Subcommands:
  list       List recent emails (JSON array)
  fetch      Download attachments from an email by UID
  mark-read  Mark an email as read by UID
  body       Print plain-text body of an email by UID

Credentials are read from environment (or dotenv):
  YUKI_EMAIL              or  AI_ASSISTANT_EMAIL
  YUKI_EMAIL_APP_PASSWORD or  AI_ASSISTANT_PASSWORD

Dotenv search order (workspace-relative):
  1. email/.env  (canonical home)
  2. travel-expenses/.env
  3. finance-tracker/.env
"""

import argparse
import email
import email.header
import imaplib
import json
import logging
import os
import re
import sys
from email.message import Message
from pathlib import Path

logger = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# ---------------------------------------------------------------------------
# Dotenv loading (optional — python-dotenv not guaranteed)
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    """Load .env files from workspace. Tries email/.env first, then project fallbacks."""
    script_dir = Path(__file__).resolve().parent
    # skills/public/email-inbox/scripts/ → workspace root is 4 levels up
    workspace = script_dir.parents[3]
    candidates = [
        workspace / "email" / ".env",
        workspace / "travel-expenses" / ".env",
        workspace / "finance-tracker" / ".env",
    ]
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
        for path in candidates:
            if path.exists():
                load_dotenv(path, override=False)
                logger.debug("Loaded dotenv from %s", path)
    except ImportError:
        logger.debug("python-dotenv not available; falling back to manual parse")
        for path in candidates:
            if path.exists():
                _parse_dotenv(path)


def _parse_dotenv(path: Path) -> None:
    """Minimal dotenv parser — sets env vars that are not already set."""
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except OSError as exc:
        logger.debug("Could not read %s: %s", path, exc)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def _get_credentials() -> tuple[str, str]:
    """Return (email, password) from environment.

    Accepts YUKI_EMAIL / YUKI_EMAIL_APP_PASSWORD or the legacy
    AI_ASSISTANT_EMAIL / AI_ASSISTANT_PASSWORD names.
    """
    email_addr = os.environ.get("YUKI_EMAIL") or os.environ.get("AI_ASSISTANT_EMAIL")
    password = os.environ.get("YUKI_EMAIL_APP_PASSWORD") or os.environ.get("AI_ASSISTANT_PASSWORD")
    if not email_addr or not password:
        sys.exit(
            "Error: email credentials not found. Set YUKI_EMAIL + YUKI_EMAIL_APP_PASSWORD "
            "(or AI_ASSISTANT_EMAIL + AI_ASSISTANT_PASSWORD) in the environment or a .env file."
        )
    return email_addr, password


# ---------------------------------------------------------------------------
# IMAP connection singleton
# ---------------------------------------------------------------------------

_imap: imaplib.IMAP4_SSL | None = None


def _get_imap() -> imaplib.IMAP4_SSL:
    """Return an authenticated IMAP4_SSL singleton; reconnects if stale."""
    global _imap
    if _imap is not None:
        try:
            status, _ = _imap.noop()
            if status == "OK":
                return _imap
            logger.debug("IMAP NOOP returned %s — reconnecting", status)
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error, OSError) as exc:
            logger.debug("IMAP connection stale: %s", exc)
        _imap = None

    email_addr, password = _get_credentials()
    logger.info("Connecting to %s:%d as %s", IMAP_HOST, IMAP_PORT, email_addr)
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(email_addr, password)
    conn.select("INBOX")
    logger.info("IMAP login successful")
    _imap = conn
    return _imap


# ---------------------------------------------------------------------------
# Header decoding helpers
# ---------------------------------------------------------------------------

def _decode_header(raw: str | bytes | None) -> str:
    """Decode an RFC2047-encoded header value to a plain Unicode string."""
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    parts = email.header.decode_header(raw)
    decoded: list[str] = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _parse_date(raw: str | None) -> str:
    """Return an ISO-8601 date string from a raw email Date header."""
    if not raw:
        return ""
    try:
        ts = email.utils.parsedate_to_datetime(raw)
        return ts.isoformat()
    except Exception as exc:
        logger.debug("Could not parse date %r: %s", raw, exc)
        return raw or ""


# ---------------------------------------------------------------------------
# Attachment detection helper
# ---------------------------------------------------------------------------

_ATTACHMENT_TYPES = {
    "application/pdf",
    "application/octet-stream",
    "application/zip",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


# ---------------------------------------------------------------------------
# Fetch a raw message by UID
# ---------------------------------------------------------------------------

def _fetch_raw(uid: str) -> bytes | None:
    """Fetch the raw RFC822 bytes for a single UID. Returns None on error."""
    conn = _get_imap()
    try:
        status, data = conn.uid("FETCH", uid, "(RFC822)")
    except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as exc:
        logger.error("FETCH failed for uid %s: %s", uid, exc)
        return None
    if status != "OK":
        logger.warning("FETCH non-OK for uid %s: %s", uid, status)
        return None
    if not data or not data[0]:
        logger.debug("Empty FETCH result for uid %s", uid)
        return None
    raw = data[0][1]
    if not isinstance(raw, bytes):
        logger.debug("Unexpected FETCH data type for uid %s: %s", uid, type(raw))
        return None
    return raw


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------

def _build_search_criteria(
    unread_only: bool,
    from_addr: str | None,
    subject_kw: str | None,
) -> str:
    """Build an IMAP SEARCH criteria string from filter options."""
    parts: list[str] = []
    if unread_only:
        parts.append("UNSEEN")
    if from_addr:
        parts.append(f'FROM "{from_addr}"')
    if subject_kw:
        parts.append(f'SUBJECT "{subject_kw}"')
    if not parts:
        return "ALL"
    return "(" + " ".join(parts) + ")"


def _fetch_email_summary(conn: imaplib.IMAP4_SSL, uid: str) -> dict | None:
    """Fetch header + size info for a single UID. Returns a summary dict or None on error."""
    try:
        status, fdata = conn.uid("FETCH", uid, "(RFC822.SIZE FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
    except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as exc:
        logger.debug("Header fetch failed for uid %s: %s", uid, exc)
        return None
    if status != "OK" or not fdata or not fdata[0]:
        logger.debug("Non-OK header fetch for uid %s", uid)
        return None

    raw_header = fdata[0][1] if isinstance(fdata[0], tuple) else b""
    if not isinstance(raw_header, bytes):
        raw_header = b""
    hdr_msg = email.message_from_bytes(raw_header)

    resp_str = fdata[0][0].decode("utf-8", errors="replace") if isinstance(fdata[0][0], bytes) else str(fdata[0][0])
    size_match = re.search(r"RFC822\.SIZE (\d+)", resp_str, re.IGNORECASE)
    size_kb = int(size_match.group(1)) // 1024 if size_match else 0
    has_att = "\\HasAttachment" in resp_str

    if not has_att:
        has_att = _check_bodystructure(conn, uid)

    return {
        "uid": uid,
        "subject": _decode_header(hdr_msg.get("Subject")),
        "from": _decode_header(hdr_msg.get("From")),
        "date": _parse_date(hdr_msg.get("Date")),
        "has_attachment": has_att,
        "size_kb": size_kb,
    }


def _check_bodystructure(conn: imaplib.IMAP4_SSL, uid: str) -> bool:
    """Return True if BODYSTRUCTURE indicates an attachment. False on error."""
    try:
        _, bsdata = conn.uid("FETCH", uid, "(BODYSTRUCTURE)")
        if bsdata and bsdata[0]:
            bs_str = bsdata[0].decode("utf-8", errors="replace") if isinstance(bsdata[0], bytes) else str(bsdata[0])
            return "attachment" in bs_str.lower()
    except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as exc:
        logger.debug("BODYSTRUCTURE fetch failed for uid %s: %s", uid, exc)
    return False


def cmd_list(args: argparse.Namespace) -> None:
    """List emails matching the given filters. Outputs a JSON array."""
    conn = _get_imap()
    criteria = _build_search_criteria(args.unread_only, args.from_addr, args.subject)

    try:
        status, data = conn.uid("SEARCH", None, criteria)
    except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as exc:
        logger.error("SEARCH failed: %s", exc)
        print(json.dumps([]))
        return

    if status != "OK":
        logger.warning("SEARCH returned status %s", status)
        print(json.dumps([]))
        return

    uid_bytes = data[0]
    if not uid_bytes:
        print(json.dumps([]))
        return

    uids = uid_bytes.split()
    limit = args.limit if args.limit > 0 else len(uids)
    uids = uids[-limit:]

    results: list[dict] = []
    for uid_b in reversed(uids):  # most-recent first
        summary = _fetch_email_summary(conn, uid_b.decode())
        if summary is not None:
            results.append(summary)

    print(json.dumps(results, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# fetch command
# ---------------------------------------------------------------------------

def cmd_fetch(args: argparse.Namespace) -> None:
    """Download all attachments from an email to output_dir. Prints JSON."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw = _fetch_raw(args.uid)
    if raw is None:
        sys.exit(f"Error: could not fetch uid {args.uid}")

    msg = email.message_from_bytes(raw)
    subject = _decode_header(msg.get("Subject"))

    attachments: list[dict] = []
    for part in msg.walk():
        disposition = part.get_content_disposition() or ""
        filename = part.get_filename()
        content_type = part.get_content_type()

        is_attachment = (
            "attachment" in disposition
            or (filename and content_type in _ATTACHMENT_TYPES)
            or (filename and content_type.startswith("audio/"))
            or (filename and content_type.startswith("image/") and "inline" not in disposition)
        )
        if not is_attachment or not filename:
            continue

        filename = _decode_header(filename)
        # Sanitize filename
        safe_name = re.sub(r'[^\w\-_. ]', '_', filename)
        dest = output_dir / safe_name
        # Avoid clobbering existing files
        counter = 1
        while dest.exists():
            stem, suffix = safe_name.rsplit(".", 1) if "." in safe_name else (safe_name, "")
            dest = output_dir / (f"{stem}_{counter}.{suffix}" if suffix else f"{stem}_{counter}")
            counter += 1

        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            logger.warning("Skipping non-bytes payload for %s in uid %s", filename, args.uid)
            continue

        try:
            dest.write_bytes(payload)
        except OSError as exc:
            logger.error("Could not write %s: %s", dest, exc)
            continue

        size_kb = len(payload) // 1024
        attachments.append({
            "filename": filename,
            "path": str(dest),
            "size_kb": size_kb,
        })
        logger.info("Saved %s (%d KB)", dest, size_kb)

    result = {
        "uid": args.uid,
        "subject": subject,
        "attachments": attachments,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# mark-read command
# ---------------------------------------------------------------------------

def cmd_mark_read(args: argparse.Namespace) -> None:
    """Mark an email as read (remove \\Unseen flag)."""
    conn = _get_imap()
    try:
        status, _data = conn.uid("STORE", args.uid, "+FLAGS", "\\Seen")
    except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as exc:
        logger.error("STORE failed for uid %s: %s", args.uid, exc)
        sys.exit(f"Error: could not mark uid {args.uid} as read: {exc}")
    if status != "OK":
        sys.exit(f"Error: STORE returned {status} for uid {args.uid}")
    result = {"uid": args.uid, "marked_read": True}
    print(json.dumps(result))
    logger.info("Marked uid %s as read", args.uid)


# ---------------------------------------------------------------------------
# body command
# ---------------------------------------------------------------------------

def _extract_text(msg: Message) -> str:
    """Extract plain-text body from a (possibly multipart) email message."""
    text_parts: list[str] = []
    for part in msg.walk():
        ctype = part.get_content_type()
        disposition = part.get_content_disposition() or ""
        if "attachment" in disposition:
            continue
        if ctype == "text/plain":
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                charset = part.get_content_charset() or "utf-8"
                text_parts.append(payload.decode(charset, errors="replace"))
        elif ctype == "text/html" and not text_parts:
            # Fallback: strip HTML tags
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                charset = part.get_content_charset() or "utf-8"
                html = payload.decode(charset, errors="replace")
                text_parts.append(_strip_html(html))
    return "\n".join(text_parts).strip()


def _strip_html(html: str) -> str:
    """Very minimal HTML stripper — removes tags and decodes common entities."""
    # Remove style/script blocks
    html = re.sub(r"<(style|script)[^>]*>.*?</(style|script)>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace block-level tags with newlines
    html = re.sub(r"<(br|p|div|tr|li|h[1-6])[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Strip all remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # Decode common HTML entities
    replacements = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&nbsp;": " ",
    }
    for entity, char in replacements.items():
        html = html.replace(entity, char)
    # Collapse whitespace
    html = re.sub(r" {2,}", " ", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def cmd_body(args: argparse.Namespace) -> None:
    """Print the plain-text body of an email."""
    raw = _fetch_raw(args.uid)
    if raw is None:
        sys.exit(f"Error: could not fetch uid {args.uid}")
    msg = email.message_from_bytes(raw)
    subject = _decode_header(msg.get("Subject"))
    from_hdr = _decode_header(msg.get("From"))
    date_hdr = _parse_date(msg.get("Date"))

    body = _extract_text(msg)

    print(f"Subject: {subject}")
    print(f"From:    {from_hdr}")
    print(f"Date:    {date_hdr}")
    print("-" * 60)
    print(body)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gmail IMAP tool — list, fetch, mark-read, body"
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: WARNING)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List recent emails")
    p_list.add_argument("--unread-only", action="store_true", help="Only show unread emails")
    p_list.add_argument("--from", dest="from_addr", metavar="SENDER", help="Filter by sender address/name")
    p_list.add_argument("--subject", metavar="KEYWORD", help="Filter by subject keyword")
    p_list.add_argument("--limit", type=int, default=20, metavar="N", help="Max results (default: 20)")

    # fetch
    p_fetch = sub.add_parser("fetch", help="Download attachments from an email")
    p_fetch.add_argument("uid", help="UID of the email")
    p_fetch.add_argument("--output-dir", required=True, metavar="DIR", help="Directory to save attachments")

    # mark-read
    p_mark = sub.add_parser("mark-read", help="Mark an email as read")
    p_mark.add_argument("uid", help="UID of the email")

    # body
    p_body = sub.add_parser("body", help="Print plain-text body of an email")
    p_body.add_argument("uid", help="UID of the email")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point."""
    _load_dotenv()

    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    dispatch = {
        "list": cmd_list,
        "fetch": cmd_fetch,
        "mark-read": cmd_mark_read,
        "body": cmd_body,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
