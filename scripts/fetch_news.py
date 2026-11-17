#!/usr/bin/env python3
"""
Fetches RSS feeds for T's News Agent and renders a static index.html.
Runs server-side (GitHub Actions) so there's no browser CORS/CSP issue.
"""
import datetime
import html
import feedparser

SECTIONS = [
    {
        "id": "markets",
        "label": "Markets",
        "glyph": "\u25b2",
        "blurb": "US stock market, tech stocks, investment advice",
        "feeds": [
            ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
            ("CNBC Markets", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
            ("MarketWatch Top", "https://www.marketwatch.com/rss/topstories"),
            ("Kiplinger", "https://www.kiplinger.com/feed/all"),
        ],
    },
    {
        "id": "world",
        "label": "World & US",
        "glyph": "\u25c8",
        "blurb": "World news, US news, US politics",
        "feeds": [
            ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
            ("NPR National", "https://feeds.npr.org/1003/rss.xml"),
            ("NPR Politics", "https://feeds.npr.org/1014/rss.xml"),
            ("Yahoo News", "https://www.yahoo.com/news/rss"),
            ("Google News", "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"),
            ("AP News", "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en"),
            ("Reuters", "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en"),
        ],
    },
    {
        "id": "tech",
        "label": "Tech",
        "glyph": "\u25c6",
        "blurb": "Tech news & the top 5\u201310 tech companies",
        "feeds": [
            ("TechCrunch", "https://techcrunch.com/feed/"),
            ("The Verge", "https://www.theverge.com/rss/index.xml"),
            ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
        ],
    },
    {
        "id": "home",
        "label": "Home Front",
        "glyph": "\u25cf",
        "blurb": "Parenting teens & college kids, caring for aging parents",
        "feeds": [
            ("NPR Life Kit", "https://feeds.npr.org/1122/rss.xml"),
            ("Next Avenue", "https://www.nextavenue.org/feed/"),
        ],
    },
    {
        "id": "career",
        "label": "Career & Growth",
        "glyph": "\u25b6",
        "blurb": "Mid-career, leadership, communication",
        "feeds": [
            ("HBR", "https://hbr.org/rss/all"),
        ],
    },
    {
        "id": "outdoors",
        "label": "Outdoors",
        "glyph": "\u25bd",
        "blurb": "Hiking news & trail reports",
        "feeds": [
            ("AllTrails Blog", "https://www.alltrails.com/blog/feed"),
        ],
    },
]

# First three render as tall tiles; the rest as short tiles in a row beneath them.
TOP_IDS = ("markets", "world", "tech")

# Public GitHub Pages URL; headings in the email and on the page link here.
PAGE_URL = "https://tsingsgits.github.io/ts-news-agent/"

MAX_PER_FEED = 6


def fetch_section_items(feeds):
    items = []
    for name, url in feeds:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:MAX_PER_FEED]:
                title = entry.get("title", "Untitled")
                link = entry.get("link", "#")
                summary_raw = entry.get("summary", "") or entry.get("description", "")
                summary = strip_tags(summary_raw)[:180]
                pub = entry.get("published", "") or entry.get("updated", "")
                pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                items.append(
                    {
                        "title": title,
                        "link": link,
                        "source": name,
                        "summary": summary,
                        "pub_struct": pub_parsed,
                        "pub_display": pub,
                    }
                )
        except Exception as e:
            print(f"  [warn] failed to fetch {name}: {e}")
    items.sort(
        key=lambda it: it["pub_struct"] or datetime.datetime.min.timetuple(),
        reverse=True,
    )
    return items


def strip_tags(text):
    import re

    text = re.sub("<[^<]+?>", "", text or "")
    return html.unescape(text).strip()


def build_rows(items):
    if not items:
        return '<li class="empty">No dispatches came through for this beat on the last run.</li>'
    row_parts = []
    for i, it in enumerate(items):
        ellipsis = "\u2026" if len(it["summary"]) >= 180 else ""
        row_parts.append(
            f'''<li class="item">
            <span class="idx">{str(i+1).zfill(2)}</span>
            <div>
                <a class="item-link" href="{html.escape(it['link'])}" target="_blank" rel="noopener noreferrer">{html.escape(it['title'])}</a>
                <p class="summary">{html.escape(it['summary'])}{ellipsis}</p>
                <div class="meta"><span>{html.escape(it['source'])}</span></div>
            </div>
        </li>'''
        )
    return "\n".join(row_parts)


STYLE_BLOCK = """<style>
  /* Broadsheet: light newsprint, ink-black serif headlines, hairline rules, one red accent. */
  :root {
    --paper: #F4F1EA; --ink: #141414; --rule: #1A1A1A; --hair: #D9D4CA;
    --muted: #4A4743; --muted2: #6B6762; --faint: #8A857D; --red: #B3261E;
    --serif: 'Newsreader', Georgia, 'Times New Roman', serif;
    --sans: 'Libre Franklin', system-ui, -apple-system, sans-serif;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--paper); color: var(--ink); font-family: var(--sans); }
  a { color: inherit; }
  header {
    max-width: 1360px; margin: 0 auto; padding: 22px 24px 16px;
    border-bottom: 3px double var(--rule); text-align: center;
  }
  .head-row { display: flex; flex-direction: column; align-items: center; gap: 6px; }
  .updated {
    order: -1; font-size: 11px; letter-spacing: .04em; color: var(--muted2);
    border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); padding: 3px 14px;
  }
  h1 {
    font-family: var(--serif); font-weight: 800; margin: 0; line-height: 1.05;
    font-size: clamp(34px, 5vw, 56px); letter-spacing: -0.02em;
  }
  .home-link { text-decoration: none; }
  .sub { margin: 6px auto 0; font-family: var(--serif); font-style: italic; font-size: 16px; color: var(--muted); }
  main {
    max-width: 1360px; margin: 0 auto; padding: 18px 24px 48px;
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .tile {
    display: flex; flex-direction: column; min-height: 0; overflow: hidden;
    border-right: 1px solid var(--rule); border-bottom: 1px solid var(--rule);
  }
  .tile:nth-child(3n+1) { border-left: 1px solid var(--rule); }
  .tile:nth-child(-n+3) { border-top: 1px solid var(--rule); }
  .tile.tall { height: 76vh; min-height: 560px; }
  .tile.short { height: 340px; }
  .tile-head { padding: 14px 16px 10px; border-bottom: 2px solid var(--rule); flex-shrink: 0; }
  .tile-title {
    font-family: var(--serif); font-size: 24px; font-weight: 700;
    display: flex; align-items: baseline; gap: 8px;
  }
  .tile-title .glyph { display: none; }
  .tile-link { text-decoration: none; }
  .tile-link:hover, .home-link:hover, .item-link:hover { color: var(--red); }
  .tile-title .count { margin-left: auto; font-family: var(--sans); font-size: 11px; font-weight: 500; color: var(--red); }
  .tile-blurb { font-size: 12px; color: var(--muted2); margin-top: 2px; }
  ul.items {
    list-style: none; margin: 0; padding: 0 16px; overflow-y: auto; flex: 1;
    scrollbar-width: thin; scrollbar-color: #C9C3B8 transparent;
  }
  .item { border-bottom: 1px solid var(--hair); padding: 12px 0; display: flex; gap: 10px; }
  .item:last-child { border-bottom: none; }
  .idx { font-family: var(--serif); font-size: 15px; font-weight: 700; color: var(--red); min-width: 22px; line-height: 1.3; }
  .item-link { text-decoration: none; font-family: var(--serif); font-size: 17px; font-weight: 700; line-height: 1.25; }
  .item:first-child .item-link { font-size: 21px; line-height: 1.18; }
  .summary {
    margin: 5px 0 0; font-size: 13px; color: var(--muted); line-height: 1.45;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }
  .meta { margin-top: 5px; font-size: 10.5px; letter-spacing: .03em; color: var(--faint); }
  .empty { color: var(--muted2); font-family: var(--serif); font-style: italic; font-size: 14px; padding: 20px 0; list-style: none; }
  footer {
    max-width: 1360px; margin: 0 auto; border-top: 3px double var(--rule);
    padding: 14px 20px; text-align: center; font-size: 12px; color: var(--muted2);
  }
  /* Narrow windows: keep three side-by-side columns, just tighter. */
  @media (max-width: 1000px) {
    header { padding: 16px 12px 12px; }
    main { padding: 12px 10px 32px; }
    .tile-head { padding: 10px 10px 8px; }
    .tile-title { font-size: 18px; }
    .tile-blurb { display: none; }
    ul.items { padding: 0 10px; }
    .idx { display: none; }
    .item-link { font-size: 14px; }
    .item:first-child .item-link { font-size: 16px; }
    .summary { font-size: 12px; -webkit-line-clamp: 3; }
    .tile.tall { height: 72vh; min-height: 460px; }
    .tile.short { height: 300px; }
  }
  /* Phones only: too narrow for three readable columns, so stack. */
  @media (max-width: 560px) {
    main { grid-template-columns: 1fr; }
    .tile { border-left: 1px solid var(--rule); }
    .tile:nth-child(n+2) { border-top: none; }
    .tile.tall { height: 70vh; min-height: 0; }
  }
</style>"""

def render_tile(s, items, size):
    count = f"{len(items)} stories" if items else ""
    return f'''<section class="tile {size}" id="tile-{s['id']}">
                <div class="tile-head">
                    <div class="tile-title"><span class="glyph">{s['glyph']}</span><a class="tile-link" href="{PAGE_URL}#tile-{s['id']}">{html.escape(s['label'])}</a><span class="count">{count}</span></div>
                    <div class="tile-blurb">{html.escape(s['blurb'])}</div>
                </div>
                <ul class="items">{build_rows(items)}</ul>
            </section>'''


def render_html(sections_data, generated_at):
    top = [s for s in SECTIONS if s["id"] in TOP_IDS]
    bottom = [s for s in SECTIONS if s["id"] not in TOP_IDS]
    tiles = [render_tile(s, sections_data[s["id"]], "tall") for s in top]
    tiles += [render_tile(s, sections_data[s["id"]], "short") for s in bottom]

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>T's News Agent</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,500;0,6..72,700;0,6..72,800;1,6..72,400&family=Libre+Franklin:wght@400;500;600&display=swap" rel="stylesheet">
{STYLE_BLOCK}
</head>
<body>
<header>
  <div class="head-row">
    <h1><a class="home-link" href="{PAGE_URL}">T&rsquo;s News Agent</a></h1>
    <span class="updated">Updated {generated_at}</span>
  </div>
  <p class="sub">A daily field brief across the fronts that matter &mdash; markets, tech, home, and the trail.</p>
</header>
<main>{"".join(tiles)}</main>
<footer>Refreshed automatically once a day via GitHub Actions.</footer>
</body>
</html>'''


def build_rows_email(items):
    """Same content as build_rows but with inline styles, since email
    clients don't reliably apply class-based CSS from <style> blocks."""
    if not items:
        return (
            '<tr><td style="color:#6B6762;font-family:Georgia,serif;font-style:italic;'
            'font-size:14px;padding:16px 0;">No dispatches came through for this beat '
            "on the last run.</td></tr>"
        )
    row_parts = []
    for i, it in enumerate(items):
        ellipsis = "\u2026" if len(it["summary"]) >= 180 else ""
        size = "20px" if i == 0 else "17px"
        border = "" if i == len(items) - 1 else "border-bottom:1px solid #D9D4CA;"
        row_parts.append(
            f'''<tr><td style="{border}padding:14px 0;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
            <td style="font-family:Georgia,serif;font-size:15px;font-weight:700;color:#B3261E;vertical-align:top;width:28px;line-height:1.3;">{str(i+1).zfill(2)}</td>
            <td>
                <a href="{html.escape(it['link'])}" style="color:#141414;text-decoration:none;font-family:Georgia,'Times New Roman',serif;font-size:{size};font-weight:700;line-height:1.25;">{html.escape(it['title'])}</a>
                <p style="margin:6px 0 0;font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#4A4743;line-height:1.5;">{html.escape(it['summary'])}{ellipsis}</p>
                <div style="margin-top:6px;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.03em;color:#8A857D;">{html.escape(it['source'])}</div>
            </td>
            </tr></table>
        </td></tr>'''
        )
    return "\n".join(row_parts)


def render_email_html(sections_data, generated_at):
    """Email clients strip <script> and most <style>, so this variant stacks
    every section with table layout and inline styles, in the Broadsheet look."""
    blocks = []
    for s in SECTIONS:
        rows = build_rows_email(sections_data[s["id"]])
        count = len(sections_data[s["id"]])
        count_txt = f"{count} stories" if count else ""
        blocks.append(
            f'''<tr><td style="padding:22px 0 0;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr><td style="border-bottom:2px solid #1A1A1A;padding-bottom:6px;">
                  <a href="{PAGE_URL}#tile-{s['id']}" style="color:#141414;text-decoration:none;font-family:Georgia,'Times New Roman',serif;font-size:24px;font-weight:700;">{html.escape(s['label'])}</a>
                  <span style="font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#B3261E;padding-left:8px;">{count_txt} &#8599;</span>
                  <div style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#6B6762;margin-top:2px;">{html.escape(s['blurb'])}</div>
                </td></tr>
                {rows}
              </table>
            </td></tr>'''
        )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light only">
<title>T's News Agent</title>
</head>
<body style="margin:0;padding:0;background:#F4F1EA;color:#141414;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F1EA;"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;padding:24px 20px 36px;">
  <tr><td align="center" style="border-bottom:3px double #1A1A1A;padding-bottom:14px;">
    <div style="display:inline-block;font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.04em;color:#6B6762;border-top:1px solid #1A1A1A;border-bottom:1px solid #1A1A1A;padding:3px 14px;">Updated {generated_at}</div>
    <h1 style="font-family:Georgia,'Times New Roman',serif;font-weight:700;font-size:38px;line-height:1.1;margin:10px 0 4px;letter-spacing:-.01em;"><a href="{PAGE_URL}" style="color:#141414;text-decoration:none;">T&rsquo;s News Agent</a></h1>
    <div style="font-family:Georgia,serif;font-style:italic;font-size:15px;color:#4A4743;">A daily field brief across the fronts that matter &mdash; markets, tech, home, and the trail.</div>
  </td></tr>
  {''.join(blocks)}
  <tr><td align="center" style="border-top:3px double #1A1A1A;margin-top:24px;padding-top:12px;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#6B6762;">
    <a href="{PAGE_URL}" style="color:#B3261E;text-decoration:none;">Read it on the web &#8599;</a> &middot; Refreshed automatically once a day via GitHub Actions.
  </td></tr>
</table>
</td></tr></table>
</body>
</html>'''


def main():
    sections_data = {}
    for s in SECTIONS:
        print(f"Fetching {s['label']}...")
        sections_data[s["id"]] = fetch_section_items(s["feeds"])

    generated_at = datetime.datetime.utcnow().strftime("%b %d, %Y %H:%M UTC")

    out = render_html(sections_data, generated_at)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(out)
    print("Wrote index.html")

    email_out = render_email_html(sections_data, generated_at)
    with open("email.html", "w", encoding="utf-8") as f:
        f.write(email_out)
    print("Wrote email.html")


if __name__ == "__main__":
    main()
