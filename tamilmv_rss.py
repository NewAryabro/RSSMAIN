import cloudscraper, time, json, os, re
from bs4 import BeautifulSoup
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree

# ================= CONFIG =================
BASE_URL = "https://www.1tamilmv.earth/"
OUT_FILE = "tamilmv.xml"
STATE_FILE = "state.json"

MAX_TOPICS = 30        # keep small for fast runtime
MAX_ITEMS = 25
DELAY = 0.5            # faster workflow

MOVIE_MAX_GB = 4
SERIES_MIN_GB = 4
# ==========================================

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

# ================= STATE ==================
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {"magnets": []}

seen = set(state.get("magnets", []))

# ================= RSS ====================
rss = Element("rss", version="2.0")
channel = SubElement(rss, "channel")

SubElement(channel, "title").text = "1TamilMV Torrent RSS"
SubElement(channel, "link").text = BASE_URL
SubElement(channel, "description").text = "Auto RSS – ≤4GB Movies / ≥4GB Series"
SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime(
    "%a, %d %b %Y %H:%M:%S GMT"
)

# ================= HELPERS =================
def is_series(title):
    t = title.lower()
    return any(x in t for x in ["season", "episode", "s01", "s02", "series"])

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

# ================= FETCH HOME =================
home = scraper.get(BASE_URL, timeout=30)
print("HOME STATUS:", home.status_code)

soup = BeautifulSoup(home.text, "lxml")
print("HOME TITLE:", soup.title)

if home.status_code != 200 or soup.title is None:
    print("⚠ Possible Cloudflare block")
    exit()

# ================= COLLECT TOPICS =================
topics = []

for a in soup.find_all("a", href=True):
    href = a["href"]

    if "topic" in href.lower():
        if not href.startswith("http"):
            href = BASE_URL.rstrip("/") + href
        topics.append(href)

topics = list(dict.fromkeys(topics))[:MAX_TOPICS]

print("TOPICS FOUND:", len(topics))

# ================= SCRAPE =================
added = 0

for url in topics:
    if added >= MAX_ITEMS:
        break

    try:
        time.sleep(DELAY)

        page = scraper.get(url, timeout=30)
        if page.status_code != 200:
            continue

        psoup = BeautifulSoup(page.text, "lxml")

        if psoup.title is None:
            continue

        raw_title = psoup.title.get_text(strip=True)
        title = clean_title(raw_title)

        size = size_from_text(title)

        # Apply size rules ONLY if size exists
        if size:
            if is_series(title):
                if size < SERIES_MIN_GB:
                    continue
            else:
                if size > MOVIE_MAX_GB:
                    continue

        # 🔥 Proper magnet extraction
        magnets = []
        for a in psoup.find_all("a", href=True):
            if a["href"].startswith("magnet:?"):
                magnets.append(a["href"])

        if not magnets:
            continue

        for magnet in magnets:
            if magnet in seen:
                continue

            item = SubElement(channel, "item")
            SubElement(item, "title").text = (
                f"{title} [{round(size,2)}GB]" if size else title
            )
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

# ================= SAVE ====================
ElementTree(rss).write(OUT_FILE, encoding="utf-8", xml_declaration=True)

with open(STATE_FILE, "w") as f:
    json.dump({"magnets": list(seen)}, f, indent=2)

print("✅ DONE | Added:", added)
