"""One-off probe: can we pull readable article text for each Markets link?"""
import re, html, json, sys
import trafilatura
from trafilatura.settings import use_config
cfg = use_config(); cfg.set("DEFAULT", "DOWNLOAD_TIMEOUT", "15")
h = open("index.html", encoding="utf-8").read()
block = re.search(r'id="tile-markets">(.*?)</section>', h, re.S).group(1)
links = re.findall(r'<a class="item-link" href="([^"]*)"[^>]*>(.*?)</a>', block, re.S)
out = []
for url, title in links:
    url = html.unescape(url)
    raw = trafilatura.fetch_url(url, config=cfg)
    text = trafilatura.extract(raw, include_comments=False, include_tables=False) if raw else None
    words = len(text.split()) if text else 0
    status = "OK" if words >= 150 else ("SHORT" if words else ("NO_HTML" if not raw else "NO_TEXT"))
    print(f"{status:8} {words:5}w  {url[:95]}")
    out.append({"url": url, "title": html.unescape(title), "status": status, "words": words, "text": text or ""})
json.dump(out, open("probe.json", "w"), indent=1)
