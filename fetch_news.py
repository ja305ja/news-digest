#!/usr/bin/env python3
"""Fetch the latest boxing headlines from public RSS/Atom feeds into data.json.

Uses only the Python standard library. Makes exactly one request per feed per run.
Stores headline, source, link and publish time only -- never article text.
"""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEEDS = [
    {"source": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/boxing/rss.xml"},
    {"source": "The Guardian", "url": "https://www.theguardian.com/sport/boxing/rss"},
    {"source": "ESPN", "url": "https://www.espn.com/espn/rss/boxing/news"},
    {"source": "Sky Sports", "url": "https://www.skysports.com/rss/12183"},
    {"source": "Bad Left Hook", "url": "https://www.badlefthook.com/rss/index.xml"},
]

DATA_FILE = Path(__file__).parent / "data.json"
MAX_PER_FEED = 15
TIMEOUT = 20
USER_AGENT = "BoxingNewsDigest/1.0 (+GitHub Pages headline reader)"
ATOM = "{http://www.w3.org/2005/Atom}"


def parse_date(text):
    """Return an ISO-8601 UTC string, or None if the date can't be read."""
    if not text:
        return None
    text = text.strip()
    dt = None
    try:
        dt = parsedate_to_datetime(text)  # RSS style: "Tue, 18 Nov 2026 10:00:00 GMT"
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))  # Atom style
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def clean(text):
    return " ".join((text or "").split())


def parse_feed(xml_bytes, source):
    root = ET.fromstring(xml_bytes)
    items = []
    if root.tag == f"{ATOM}feed":  # Atom
        for entry in root.findall(f"{ATOM}entry"):
            link = ""
            for l in entry.findall(f"{ATOM}link"):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href", "")
                    break
            items.append({
                "title": clean(entry.findtext(f"{ATOM}title")),
                "link": link.strip(),
                "published": parse_date(entry.findtext(f"{ATOM}published")
                                        or entry.findtext(f"{ATOM}updated")),
            })
    else:  # RSS 2.0
        for item in root.iter("item"):
            items.append({
                "title": clean(item.findtext("title")),
                "link": (item.findtext("link") or "").strip(),
                "published": parse_date(item.findtext("pubDate")
                                        or item.findtext("{http://purl.org/dc/elements/1.1/}date")),
            })
    items = [dict(i, source=source) for i in items
             if i["title"] and i["link"].startswith(("http://", "https://"))]
    return items[:MAX_PER_FEED]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def load_previous():
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main():
    previous = load_previous()
    old_items = previous.get("items", [])
    all_items, statuses = [], []

    for feed in FEEDS:
        source = feed["source"]
        try:
            items = parse_feed(fetch(feed["url"]), source)
            if not items:
                raise ValueError("feed returned no headlines")
            all_items.extend(items)
            statuses.append({"source": source, "ok": True, "count": len(items)})
            print(f"OK    {source}: {len(items)} headlines")
        except Exception as exc:  # one bad feed must not stop the others
            # Keep that source's headlines from the last good run so the page isn't empty.
            kept = [i for i in old_items if i.get("source") == source]
            all_items.extend(kept)
            statuses.append({"source": source, "ok": False, "count": len(kept),
                             "error": type(exc).__name__})
            print(f"FAIL  {source}: {exc} (kept {len(kept)} older headlines)", file=sys.stderr)

    # De-duplicate by link, then sort newest first (undated items go last).
    unique = {}
    for item in all_items:
        unique.setdefault(item["link"], item)
    items = sorted(unique.values(), key=lambda i: i.get("published") or "", reverse=True)

    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "feeds": statuses,
        "items": items,
    }
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {len(items)} headlines to {DATA_FILE.name}")


if __name__ == "__main__":
    main()
