import cloudscraper, time, json, os, re
from bs4 import BeautifulSoup
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree

BASE_URL = "https://www.1tamilmv.rsvp/"
OUT_FILE = "tamilmv.xml"
STATE_FILE = "state.json"

scraper = cloudscraper.create_scraper()

# ===== LOAD STATE =====
if os.path.exists(STATE_FILE):
    state = json.load(open(STATE_FILE))
else:
    state = {"magnets": []}

seen = set(state["magnets"])

# ===== RSS =====
rss = Element("rss", version="2.0")
channel = SubElement(rss, "channel")
SubElement(channel, "title").text = "1TamilMV Torrent RSS"
SubElement(channel, "link").text = BASE_URL
SubElement(channel, "description").text = "Auto RSS – Magnet Based"
SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime(
    "%a, %d %b %Y %H:%M:%S GMT"
)

# ===== FETCH HOME =====
home = scraper.get(BASE_URL, timeout=30)
soup = BeautifulSoup(home.text, "lxml")

topic_links = set()

for a in soup.find_all("a", href=True):
    href = a["href"]
    if "/topic/" in href:
        if not href.startswith("http"):
            href = BASE_URL.rstrip("/") + href
        topic_links.add(href)

print("TOPICS FOUND:", len(topic_links))

# ===== SCRAPE TOPICS =====
added = 0

for url in list(topic_links)[:50]:
    time.sleep(2)
    page = scraper.get(url, timeout=30)
    psoup = BeautifulSoup(page.text, "lxml")

    title = psoup.title.text.strip()

    # 🔥 BEST WAY → REGEX
    magnets = re.findall(r"(magnet:\?[^\s\"'<]+)", page.text)

    for magnet in magnets:
        if magnet in seen:
            continue

        item = SubElement(channel, "item")
        SubElement(item, "title").text = title
        SubElement(item, "link").text = magnet
        SubElement(item, "guid").text = magnet
        SubElement(item, "pubDate").text = datetime.utcnow().strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )

        seen.add(magnet)
        added += 1
        print("➕", title)

        if added >= 25:
            break

    if added >= 25:
        break

# ===== SAVE =====
ElementTree(rss).write(OUT_FILE, encoding="utf-8", xml_declaration=True)
json.dump({"magnets": list(seen)}, open(STATE_FILE, "w"), indent=2)

print("✅ DONE | Added:", added)
