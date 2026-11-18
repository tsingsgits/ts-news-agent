"""Pull today's market newsletters from a Gmail inbox over IMAP.

Reads the newest issue of each newsletter in NEWSLETTERS from the inbox
named by the NEWSLETTER_IMAP_USER / NEWSLETTER_IMAP_PASSWORD environment
variables (a Gmail address and a Gmail app password). Returns one card per
newsletter: subject, received time, a short intro, a few top headlines and
a link to read the full issue on the web.

Nothing is stored or forwarded: the inbox is only read.
"""

import datetime
import email
import email.policy
import email.utils
import html
import imaplib
import os
import re
from html.parser import HTMLParser

# How far back to look for each newsletter's latest issue.
LOOKBACK_DAYS = 2

# sender_patterns match the From address (case-insensitive substring).
# subject_must (optional) is a regex the subject must match, for senders
# that send several newsletters. web_home is used when the issue has no
# "view in browser" link.
NEWSLETTERS = [
    {
        "name": "Axios Markets",
        "sender_patterns": ["axios.com"],
        "subject_must": None,
        "web_home": "https://www.axios.com/newsletters/axios-markets",
    },
    {
        "name": "Morning Brew",
        "sender_patterns": ["morningbrew.com"],
        "subject_must": None,
        "web_home": "https://www.morningbrew.com/",
    },
    {
        "name": "Robinhood Snacks",
        "sender_patterns": ["snacks.robinhood.com", "sherwood.news"],
        "subject_must": None,
        "web_home": "https://sherwood.news/snacks/newsletters/",
    },
    {
        "name": "The Daily Upside",
        "sender_patterns": ["thedailyupside.com"],
        "subject_must": None,
        "web_home": "https://www.thedailyupside.com/",
    },
    {
        "name": "Money Stuff",
        "sender_patterns": ["bloomberg"],
        "subject_must": r"(?i)money stuff",
        "web_home": "https://www.bloomberg.com/account/newsletters/money-stuff",
    },
]

# Sign-up and housekeeping mail that should never show up as an issue.
SKIP_SUBJECT = re.compile(
    r"(?i)\b(welcome|confirm|verify|verification|action required|thank you for "
    r"subscribing|thanks for subscribing|you're in|you are in|password|account|"
    r"receipt|unsubscribe)\b"
)

# Lines that look like headings but are newsletter furniture.
BOILERPLATE = re.compile(
    r"(?i)(presented by|sponsored|advertis|together with|brought to you|"
    r"unsubscribe|view in browser|view online|read online|share this|"
    r"refer|forward(ed)?|subscribe|sign up|download|follow us|privacy|"
    r"manage preferences|update your|in partnership|partner|^today'?s|"
    r"^good morning|^hi |^hello|^welcome|^\W*$)"
)

# Welcome mail that slips past SKIP_SUBJECT is caught by its opening lines.
WELCOME_BODY = re.compile(r"(?i)(thanks? (you )?for (signing up|subscribing|joining)|"
                          r"welcome to (the )?|you('| a)re (now )?(subscribed|part of)|"
                          r"confirm your (subscription|email))")

VIEW_ONLINE = re.compile(r"(?i)(view (it )?(in|on) (your )?(browser|web)|view online|"
                         r"read online|read in browser|web version|view as (a )?web ?page)")


class _Extract(HTMLParser):
    """Collect visible text blocks, heading-like blocks and links."""

    BLOCK = {"p", "div", "td", "li", "h1", "h2", "h3", "h4", "tr", "table", "br"}
    HEAD = {"h1", "h2", "h3"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.blocks = []        # (text, is_heading)
        self.links = []         # (href, text)
        self._buf = []
        self._head_depth = 0
        self._strong_depth = 0
        self._strong_only = True
        self._a_href = None
        self._a_text = []
        self._block_all_strong = True

    def _flush(self):
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        if text:
            self.blocks.append((text, self._head_depth > 0 or self._strong_only_block))
        self._buf = []

    @property
    def _strong_only_block(self):
        return getattr(self, "_block_all_strong", False)

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head", "title"):
            self.skip += 1
            return
        if tag in self.BLOCK:
            self._flush()
            self._block_all_strong = True
        if tag in self.HEAD:
            self._head_depth += 1
        if tag in ("strong", "b"):
            self._strong_depth += 1
        if tag == "a":
            self._a_href = dict(attrs).get("href")
            self._a_text = []

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head", "title"):
            self.skip = max(0, self.skip - 1)
            return
        if tag == "a" and self._a_href:
            self.links.append((self._a_href, re.sub(r"\s+", " ", "".join(self._a_text)).strip()))
            self._a_href = None
        if tag in ("strong", "b"):
            self._strong_depth = max(0, self._strong_depth - 1)
        if tag in self.BLOCK:
            self._flush()
            self._block_all_strong = True
        if tag in self.HEAD:
            self._head_depth = max(0, self._head_depth - 1)

    def handle_data(self, data):
        if self.skip:
            return
        if data.strip():
            if self._strong_depth == 0 and self._head_depth == 0:
                self._block_all_strong = False
        self._buf.append(data)
        if self._a_href is not None:
            self._a_text.append(data)


def _decode(value):
    """Header value as plain text (the default policy already decodes it)."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _html_part(msg):
    html_body, text_body = None, None
    for part in msg.walk():
        ctype = part.get_content_type()
        if part.get_content_maintype() == "multipart":
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        body = payload.decode(charset, errors="replace")
        if ctype == "text/html" and html_body is None:
            html_body = body
        elif ctype == "text/plain" and text_body is None:
            text_body = body
    if html_body is None and text_body is not None:
        html_body = "<p>" + html.escape(text_body).replace("\n\n", "</p><p>") + "</p>"
    return html_body or ""


def parse_issue(raw_html, subject, web_home):
    """Return intro, headlines and a web link from one newsletter's HTML."""
    p = _Extract()
    try:
        p.feed(raw_html)
        p._flush()
    except Exception:
        pass

    # Web version link if the issue offers one; otherwise the newsletter home.
    link = web_home
    for href, text in p.links:
        if href and href.startswith("http") and VIEW_ONLINE.search(text or ""):
            link = href
            break

    subj_norm = subject.lower().strip()
    headlines, seen = [], set()
    for text, is_head in p.blocks:
        t = text.strip(" ‌͏ ")
        if not is_head or not (14 <= len(t) <= 140):
            continue
        if BOILERPLATE.search(t) or t.lower() == subj_norm:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        headlines.append(t)
        if len(headlines) == 4:
            break

    intro = ""
    for text, is_head in p.blocks:
        t = text.strip(" ‌͏ ")
        if is_head or len(t) < 80 or BOILERPLATE.search(t[:40]):
            continue
        intro = t
        break
    if len(intro) > 240:
        intro = intro[:237].rsplit(" ", 1)[0] + "…"

    return {"intro": intro, "headlines": headlines, "link": link}


def fetch_newsletters():
    """Return a list of issue dicts, newest issue per newsletter.

    Returns None when the inbox credentials are not configured, and [] when
    nothing was found, so callers can show the right message.
    """
    user = os.environ.get("NEWSLETTER_IMAP_USER", "").strip()
    password = os.environ.get("NEWSLETTER_IMAP_PASSWORD", "").replace(" ", "").strip()
    if not user or not password:
        print("Newsletters: inbox not configured (NEWSLETTER_IMAP_USER / _PASSWORD); skipping.")
        return None

    since = (datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
    issues = []
    try:
        conn = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=30)
        conn.login(user, password)
        conn.select('"[Gmail]/All Mail"', readonly=True)
        for nl in NEWSLETTERS:
            best = None
            for pat in nl["sender_patterns"]:
                typ, data = conn.search(None, "SINCE", since, "FROM", f'"{pat}"')
                if typ != "OK":
                    continue
                ids = data[0].split()
                for num in reversed(ids[-15:]):
                    typ, msg_data = conn.fetch(num, "(RFC822)")
                    if typ != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                        continue
                    msg = email.message_from_bytes(msg_data[0][1], policy=email.policy.default)
                    subject = _decode(msg.get("Subject"))
                    if SKIP_SUBJECT.search(subject):
                        continue
                    if nl["subject_must"] and not re.search(nl["subject_must"], subject):
                        continue
                    body_html = _html_part(msg)
                    opening = re.sub(r"\s+", " ", re.sub(r"<[^>]+>|&[#\w]+;", " ",
                                     re.sub(r"(?is)<(style|script|head)\b.*?</\1>", " ", body_html)))[:700]
                    if WELCOME_BODY.search(opening):
                        continue
                    try:
                        when = email.utils.parsedate_to_datetime(msg.get("Date"))
                    except Exception:
                        when = None
                    if when and when.tzinfo is None:
                        when = when.replace(tzinfo=datetime.timezone.utc)
                    if best is None or (when and best["when"] and when > best["when"]):
                        best = {"msg": msg, "subject": subject, "when": when, "html": body_html}
                    break  # newest acceptable message for this pattern
            if best is None:
                print(f"Newsletters: no recent issue of {nl['name']}.")
                continue
            parsed = parse_issue(best["html"], best["subject"], nl["web_home"])
            issues.append({
                "name": nl["name"],
                "subject": best["subject"],
                "when": best["when"],
                **parsed,
            })
            print(f"Newsletters: {nl['name']} — {best['subject']!r}, {len(parsed['headlines'])} headlines.")
        conn.logout()
    except Exception as exc:  # never let the inbox break the daily page
        print(f"Newsletters: could not read inbox ({type(exc).__name__}: {exc}).")
        return issues

    issues.sort(key=lambda i: i["when"] or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
                reverse=True)
    return issues
