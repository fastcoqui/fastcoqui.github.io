#!/usr/bin/env python3
"""Fetch Tesla news from public RSS feeds and write news.json (stdlib only, no keys)."""
import json, re, html, sys, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

FEEDS = [
    ("Electrek", "https://electrek.co/guides/tesla/feed/"),
    ("Teslarati", "https://www.teslarati.com/feed/"),
    ("Not a Tesla App", "https://www.notateslaapp.com/rss"),
    ("InsideEVs", "https://insideevs.com/rss/make/tesla/"),
]
KEEP = 12
TESLA = re.compile(r"\b(tesla|model [3ysx]|cybertruck|cybercab|robotaxi|fsd|supercharg|optimus|powerwall|megapack|roadster)", re.I)
NS = {"media": "http://search.yahoo.com/mrss/", "content": "http://purl.org/rss/1.0/modules/content/"}
UA = {"User-Agent": "Mozilla/5.0 (fastcoqui news bot; +https://fastcoqui.github.io/)"}

def clean(s, n=None):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    if n and len(s) > n:
        s = s[:n].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return s

def image(it):
    for tag in ("media:content", "media:thumbnail"):
        e = it.find(tag, NS)
        if e is not None and e.get("url"): return e.get("url")
    e = it.find("enclosure")
    if e is not None and (e.get("type") or "").startswith("image"): return e.get("url")
    m = re.search(r'<img[^>]+src="([^"]+)"', (it.findtext("content:encoded", "", NS) or "") + (it.findtext("description") or ""))
    return m.group(1) if m else None

def norm(u): return re.sub(r"[?#].*$", "", u or "").rstrip("/").lower()

items, ok = [], []
for name, url in FEEDS:
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read()
        root = ET.fromstring(raw)
        n = 0
        for it in root.iter("item"):
            title, link = clean(it.findtext("title")), (it.findtext("link") or "").strip()
            desc = clean(it.findtext("description"), 180)
            if not title or not link: continue
            if not TESLA.search(title): continue
            try: dt = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
            except Exception: continue
            items.append({"title": title, "source": name, "link": link, "date": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                          "snippet": desc, "image": image(it)})
            n += 1
            if n >= 30: break
        ok.append(name)
    except Exception as e:
        print(f"WARN {name}: {e}", file=sys.stderr)

seen, out = set(), []
for it in sorted(items, key=lambda x: x["date"], reverse=True):
    k1, k2 = norm(it["link"]), re.sub(r"\W+", "", it["title"].lower())[:60]
    if k1 in seen or k2 in seen: continue
    seen.update({k1, k2}); out.append(it)
    if len(out) >= KEEP: break

if not out:
    sys.exit("No items fetched; keeping existing news.json")

path = "news.json"
try: old = json.load(open(path))
except Exception: old = {}
if old.get("items") == out:
    print("No change"); sys.exit(0)
json.dump({"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "sources": ok, "items": out},
          open(path, "w"), ensure_ascii=False, indent=1)
print(f"Wrote {len(out)} items from {ok}")
