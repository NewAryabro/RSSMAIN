import cloudscraper, time, json, os, re
from bs4 import BeautifulSoup
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree

# =============== CONFIG =================
BASE_URL = "https://www.1tamilmv.rsvp/"
OUT_FILE = "tamilmv.xml"
STATE_FILE = "state.json"

MAX_TOPICS = 50
MAX_ITEMS = 25
DELAY = 2

MOVIE_MAX_GB = 4
SERIES_MIN_GB = 4
# =======================================

scraper = cloudscraper.create_scraper()

# =============== STATE ==================
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {"magnets": []}

seen = set(state.get("magnets", []))

# =============== RSS ====================
rss = Element("rss", version="2.0")
channel = SubElement(rss, "channel")

SubElement(channel, "title").text = "1TamilMV Torrent RSS"
SubElement(channel, "link").text = BASE_URL
SubElement(channel, "description").text = "Auto RSS – Filtered – ≤4GB Movies"
SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime(
    "%a, %d %b %Y %H:%M:%S GMT"
)

# =============== HELPERS =================
def is_series(title):
    t = title.lower()
    return any(x in t for x in ["season", "s01", "s02", "episode", "ep", "series"])

def size_from_text(text):
    m = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB)', text.upper())
    if not m:
        return None
    size = float(m.group(1))
    if m.group(2) == "MB":
        size /= 1024
    return size

def clean_title(title):
    return re.sub(r"1TamilMV\s*[-–]\s*", "", title).strip()

# =============== FETCH HOME ==============
home = scraper.get(BASE_URL, timeout=30)
soup = BeautifulSoup(home.text, "lxml")

topics = set()
for a in soup.find_all("a", href=True):
    href = a["href"]
    if "/topic/" in href:
        if not href.startswith("http"):
            href = BASE_URL.rstrip("/") + href
        topics.add(href)

topics = list(topics)[:MAX_TOPICS]
print("TOPICS FOUND:", len(topics))

# =============== SCRAPE ==================
added = 0

for url in topics:
    if added >= MAX_ITEMS:
        break

    try:
        time.sleep(DELAY)
        page = scraper.get(url, timeout=30)
        html = page.text
        psoup = BeautifulSoup(html, "lxml")

        raw_title = psoup.title.get_text(strip=True)
        title = clean_title(raw_title)

        size = size_from_text(title)
        if size is None:
            continue

        if is_series(title):
            if size < SERIES_MIN_GB:
                continue
        else:
            if size > MOVIE_MAX_GB:
                continue

        magnets = re.findall(r"(magnet:\?[^\s\"'<]+)", html)

        for magnet in magnets:
            if magnet in seen:
                continue

            item = SubElement(channel, "item")
            SubElement(item, "title").text = f"{title} [{round(size,2)}GB]"
            SubElement(item, "link").text = magnet
            SubElement(item, "guid").text = magnet
            SubElement(item, "pubDate").text = datetime.utcnow().strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )

            seen.add(magnet)
            added += 1
            print("➕ ADDED:", title)

            if added >= MAX_ITEMS:
                break

    except Exception as e:
        print("ERROR:", url, e)

# =============== SAVE ====================
ElementTree(rss).write(OUT_FILE, encoding="utf-8", xml_declaration=True)

with open(STATE_FILE, "w") as f:
    json.dump({"magnets": list(seen)}, f, indent=2)

print("✅ DONE | Added:", added)
