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
        "id": "world",
        "label": "World & US",
        "glyph": "\u25c8",
        "blurb": "World news, US news, US politics",
        "feeds": [
            ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
            ("NPR National", "https://feeds.npr.org/1003/rss.xml"),
            ("NPR Politics", "https://feeds.npr.org/1014/rss.xml"),
        ],
    },
    {
        "id": "markets",
        "label": "Markets",
        "glyph": "\u25b2",
        "blurb": "US stock market, tech stocks, investment advice",
        "feeds": [
            ("CNBC Markets", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
            ("MarketWatch Top", "https://www.marketwatch.com/rss/topstories"),
            ("Kiplinger", "https://www.kiplinger.com/feed/all"),
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


def render_html(sections_data, generated_at):
    tab_buttons = "\n".join(
        f'''<button class="tab-btn" data-target="{s['id']}" onclick="showSection('{s['id']}')">
            <span class="glyph">{s['glyph']}</span>{html.escape(s['label'])}
        </button>'''
        for s in SECTIONS
    )

    panels = []
    for s in SECTIONS:
        items = sections_data[s["id"]]
        if items:
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
            rows = "\n".join(row_parts)
        else:
            rows = '<li class="empty">No dispatches came through for this beat on the last run.</li>'
        panels.append(
            f'''<section class="panel" id="panel-{s['id']}">
                <div class="panel-head">
                    <div class="panel-title">{html.escape(s['label'])}</div>
                    <div class="panel-blurb">{html.escape(s['blurb'])}</div>
                </div>
                <ul class="items">{rows}</ul>
            </section>'''
        )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>T's News Agent</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0F1614; --surface: #1D2A25; --border: #2A3530;
    --text: #E8E4DA; --muted: #9AA79E; --muted2: #7E8B84;
    --amber: #C08A3E; --sage: #5C7A6E;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font-family: 'Inter', system-ui, sans-serif;
  }}
  header {{
    border-bottom: 1px solid var(--border);
    padding: 28px 20px 20px; max-width: 880px; margin: 0 auto;
  }}
  h1 {{
    font-family: 'Fraunces', serif; font-weight: 700;
    font-size: clamp(28px, 5vw, 38px); margin: 0; letter-spacing: -0.01em;
  }}
  .sub {{ margin: 6px 0 0; color: var(--muted); font-size: 14px; max-width: 560px; }}
  .updated {{
    font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: var(--muted);
  }}
  .head-row {{ display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; }}
  nav {{
    max-width: 880px; margin: 0 auto; display: flex; gap: 6px;
    overflow-x: auto; padding: 14px 20px 0;
  }}
  .tab-btn {{
    flex-shrink: 0; background: transparent; color: var(--muted2);
    border: 1px solid var(--border); border-radius: 999px; padding: 8px 14px;
    font-size: 13px; font-family: 'Inter', sans-serif; font-weight: 500;
    cursor: pointer; display: flex; align-items: center; gap: 6px;
  }}
  .tab-btn.active {{ background: var(--surface); color: var(--text); border-color: #C08A3E66; }}
  .tab-btn .glyph {{ color: var(--sage); }}
  .tab-btn.active .glyph {{ color: var(--amber); }}
  main {{ max-width: 880px; margin: 0 auto; padding: 20px 20px 60px; }}
  .panel {{ display: none; }}
  .panel.active {{ display: block; }}
  .panel-head {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 10px;
  }}
  .panel-title {{ font-family: 'Fraunces', serif; font-size: 20px; font-weight: 600; }}
  .panel-blurb {{ font-size: 13px; color: var(--muted2); }}
  ul.items {{ list-style: none; margin: 0; padding: 0; }}
  .item {{
    border-bottom: 1px solid #1E2622; padding: 16px 0; display: flex; gap: 14px;
  }}
  .idx {{
    font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--sage);
    min-width: 26px; padding-top: 3px;
  }}
  .item-link {{
    color: var(--text); text-decoration: none; font-family: 'Fraunces', serif;
    font-size: 17px; font-weight: 600; line-height: 1.3;
  }}
  .item-link:hover {{ color: var(--amber); }}
  .summary {{ margin: 6px 0 0; font-size: 14px; color: var(--muted); line-height: 1.5; }}
  .meta {{
    margin-top: 6px; font-family: 'IBM Plex Mono', monospace; font-size: 11px;
    color: var(--sage); display: flex; gap: 10px;
  }}
  .empty {{ color: var(--muted2); font-size: 14px; padding: 24px 0; list-style: none; }}
  footer {{
    border-top: 1px solid var(--border); padding: 14px 20px; text-align: center;
    font-size: 12px; color: var(--sage); font-family: 'IBM Plex Mono', monospace;
  }}
</style>
</head>
<body>
<header>
  <div class="head-row">
    <h1>T&rsquo;s News Agent</h1>
    <span class="updated">Updated {generated_at}</span>
  </div>
  <p class="sub">A daily field brief across the fronts that matter &mdash; markets, tech, home, and the trail.</p>
</header>
<nav>{tab_buttons}</nav>
<main>{''.join(panels)}</main>
<footer>Refreshed automatically once a day via GitHub Actions.</footer>
<script>
  function showSection(id) {{
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('panel-' + id).classList.add('active');
    document.querySelector('.tab-btn[data-target="' + id + '"]').classList.add('active');
    localStorage.setItem('ts-news-active-tab', id);
  }}
  const saved = localStorage.getItem('ts-news-active-tab') || '{SECTIONS[0]['id']}';
  showSection(saved);
</script>
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


if __name__ == "__main__":
    main()
