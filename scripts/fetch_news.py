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
  :root {
    --bg: #0F1614; --surface: #16201C; --surface2: #1D2A25; --border: #2A3530;
    --text: #E8E4DA; --muted: #9AA79E; --muted2: #7E8B84;
    --amber: #C08A3E; --sage: #5C7A6E;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: 'Inter', system-ui, sans-serif;
  }
  header {
    border-bottom: 1px solid var(--border);
    padding: 24px 24px 18px; max-width: 1360px; margin: 0 auto;
  }
  h1 {
    font-family: 'Fraunces', serif; font-weight: 700;
    font-size: clamp(26px, 4vw, 36px); margin: 0; letter-spacing: -0.01em;
  }
  .sub { margin: 6px 0 0; color: var(--muted); font-size: 14px; }
  .updated { font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: var(--muted); }
  .head-row { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; }
  main {
    max-width: 1360px; margin: 0 auto; padding: 20px 24px 48px;
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px;
  }
  .tile {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    display: flex; flex-direction: column; min-height: 0; overflow: hidden;
  }
  .tile.tall { height: 76vh; min-height: 560px; }
  .tile.short { height: 340px; }
  .tile-head {
    padding: 14px 16px 10px; border-bottom: 1px solid var(--border);
    background: var(--surface2); flex-shrink: 0;
  }
  .tile-title {
    font-family: 'Fraunces', serif; font-size: 19px; font-weight: 600;
    display: flex; align-items: center; gap: 8px;
  }
  .tile-title .glyph { color: var(--amber); font-size: 14px; }
  .tile-title .count {
    margin-left: auto; font-family: 'IBM Plex Mono', monospace; font-size: 11px;
    font-weight: 400; color: var(--sage);
  }
  .tile-blurb { font-size: 12px; color: var(--muted2); margin-top: 3px; }
  ul.items {
    list-style: none; margin: 0; padding: 0 16px; overflow-y: auto; flex: 1;
    scrollbar-width: thin; scrollbar-color: var(--border) transparent;
  }
  .item { border-bottom: 1px solid #1E2622; padding: 12px 0; display: flex; gap: 10px; }
  .item:last-child { border-bottom: none; }
  .idx {
    font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--sage);
    min-width: 20px; padding-top: 3px;
  }
  .item-link {
    color: var(--text); text-decoration: none; font-family: 'Fraunces', serif;
    font-size: 15px; font-weight: 600; line-height: 1.3;
  }
  .item-link:hover { color: var(--amber); }
  .summary {
    margin: 4px 0 0; font-size: 13px; color: var(--muted); line-height: 1.45;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }
  .meta { margin-top: 5px; font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--sage); }
  .empty { color: var(--muted2); font-size: 13px; padding: 20px 0; list-style: none; }
  footer {
    border-top: 1px solid var(--border); padding: 14px 20px; text-align: center;
    font-size: 12px; color: var(--sage); font-family: 'IBM Plex Mono', monospace;
  }
  /* Narrow windows: keep three side-by-side columns, just tighter. */
  @media (max-width: 1000px) {
    header { padding: 18px 14px 14px; }
    main { gap: 10px; padding: 14px 12px 32px; }
    .tile-head { padding: 10px 10px 8px; }
    .tile-title { font-size: 16px; }
    .tile-title .count, .tile-blurb { display: none; }
    ul.items { padding: 0 10px; }
    .idx { display: none; }
    .item-link { font-size: 13.5px; }
    .summary { font-size: 12px; -webkit-line-clamp: 3; }
    .tile.tall { height: 72vh; min-height: 460px; }
    .tile.short { height: 300px; }
  }
  /* Phones only: too narrow for three readable columns, so stack. */
  @media (max-width: 560px) {
    main { grid-template-columns: 1fr; }
    .tile.tall { height: 70vh; min-height: 0; }
  }
</style>"""

def render_tile(s, items, size):
    count = f"{len(items)} stories" if items else ""
    return f'''<section class="tile {size}" id="tile-{s['id']}">
                <div class="tile-head">
                    <div class="tile-title"><span class="glyph">{s['glyph']}</span>{html.escape(s['label'])}<span class="count">{count}</span></div>
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
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
{STYLE_BLOCK}
</head>
<body>
<header>
  <div class="head-row">
    <h1>T&rsquo;s News Agent</h1>
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
            '<li style="color:#7E8B84;font-size:14px;padding:24px 0;'
            'list-style:none;">No dispatches came through for this beat '
            "on the last run.</li>"
        )
    row_parts = []
    for i, it in enumerate(items):
        ellipsis = "\u2026" if len(it["summary"]) >= 180 else ""
        row_parts.append(
            f'''<li style="border-bottom:1px solid #1E2622;padding:16px 0;list-style:none;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
            <td style="font-family:monospace;font-size:12px;color:#5C7A6E;vertical-align:top;width:26px;">{str(i+1).zfill(2)}</td>
            <td>
                <a href="{html.escape(it['link'])}" style="color:#E8E4DA;text-decoration:none;font-family:Georgia,serif;font-size:17px;font-weight:600;">{html.escape(it['title'])}</a>
                <p style="margin:6px 0 0;font-size:14px;color:#9AA79E;line-height:1.5;">{html.escape(it['summary'])}{ellipsis}</p>
                <div style="margin-top:6px;font-family:monospace;font-size:11px;color:#5C7A6E;">{html.escape(it['source'])}</div>
            </td>
            </tr></table>
        </li>'''
        )
    return "\n".join(row_parts)


def render_email_html(sections_data, generated_at):
    """Email clients strip <script> tags, so the tabbed JS-driven layout
    renders as empty. This variant stacks every section, always visible,
    with no JS or tab nav required, using inline styles throughout."""
    blocks = []
    for s in SECTIONS:
        rows = build_rows_email(sections_data[s["id"]])
        blocks.append(
            f'''<section style="margin-bottom:28px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;border-bottom:1px solid #2A3530;padding-bottom:10px;">
                    <div style="font-family:Georgia,serif;font-size:20px;font-weight:600;color:#E8E4DA;">{html.escape(s['glyph'])} {html.escape(s['label'])}</div>
                </div>
                <div style="font-size:13px;color:#7E8B84;margin-bottom:10px;">{html.escape(s['blurb'])}</div>
                <ul style="list-style:none;margin:0;padding:0;">{rows}</ul>
            </section>'''
        )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>T's News Agent</title>
</head>
<body style="margin:0;background:#0F1614;color:#E8E4DA;font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:640px;margin:0 auto;padding:28px 20px 40px;">
  <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;border-bottom:1px solid #2A3530;padding-bottom:16px;margin-bottom:20px;">
    <h1 style="font-family:Georgia,serif;font-weight:700;font-size:30px;margin:0;color:#E8E4DA;">T&rsquo;s News Agent</h1>
    <span style="font-size:13px;color:#9AA79E;">Updated {generated_at}</span>
  </div>
  <p style="margin:0 0 24px;color:#9AA79E;font-size:14px;">A daily field brief across the fronts that matter &mdash; markets, tech, home, and the trail.</p>
  {''.join(blocks)}
  <div style="border-top:1px solid #2A3530;padding-top:14px;text-align:center;font-size:12px;color:#5C7A6E;">
    Refreshed automatically once a day via GitHub Actions.
  </div>
</div>
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
