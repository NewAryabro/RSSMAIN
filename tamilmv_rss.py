import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree
import time
import json
import os

BASE_URL = "https://www.1tamilmv.lc/"
OUT_FILE = "tamilmv.xml"
STATE_FILE = "state.json"

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

# Load state
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {"processed": []}

processed = set(state.get("processed", []))

rss = Element("rss", version="2.0")
channel = SubElement(rss, "channel")

SubElement(channel, "title").text = "1TamilMV TORRENT RSS"
SubElement(channel, "link").text = BASE_URL
SubElement(channel, "description").text = "Experimental auto torrent RSS"
SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime(
    "%a, %d %b %Y %H:%M:%S GMT"
)

# Load homepage
home = scraper.get(BASE_URL, timeout=30)
soup = BeautifulSoup(home.text, "lxml")

posts = []
for a in soup.find_all("a", href=True):
    if "forums/topic" in a["href"]:
        posts.append((a.get_text(strip=True), a["href"]))

posts = posts[:8]  # SAFE LIMIT

for title, post_url in posts:
    if post_url in processed:
        continue

    try:
        time.sleep(6)  # anti-ban delay

        post = scraper.get(post_url, timeout=30)
        psoup = BeautifulSoup(post.text, "lxml")

        torrent = None
        for a in psoup.find_all("a", href=True):
            h = a["href"]
            if h.startswith("magnet:?") or h.endswith(".torrent"):
                torrent = h
                break

        if not torrent:
            continue

        item = SubElement(channel, "item")
        SubElement(item, "title").text = title
        SubElement(item, "link").text = torrent
        SubElement(item, "guid").text = torrent
        SubElement(item, "pubDate").text = datetime.utcnow().strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

        processed.add(post_url)
        print("ADDED:", title)

    except Exception as e:
        print("SKIPPED:", title, e)

# Save RSS
ElementTree(rss).write(OUT_FILE, encoding="utf-8", xml_declaration=True)

# Save state
with open(STATE_FILE, "w") as f:
    json.dump({"processed": list(processed)}, f, indent=2)

print("DONE")
