import time, json, os, re
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# ================= CONFIG =================
BASE_URL = "https://www.1tamilmv.cymru/"
OUT_FILE = "tamilmv.xml"
STATE_FILE = "state.json"

MAX_TOPICS = 20
MAX_ITEMS = 25

# ================= STATE =================
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {"magnets": []}

seen = set(state.get("magnets", []))

# ================= RSS =================
rss = Element("rss", version="2.0")
channel = SubElement(rss, "channel")

SubElement(channel, "title").text = "TamilMV RSS"
SubElement(channel, "link").text = BASE_URL
SubElement(channel, "description").text = "Auto RSS Playwright Scraper"
SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime(
    "%a, %d %b %Y %H:%M:%S GMT"
)

# ================= HELPERS =================
def clean_title(title):
    return re.sub(r"1TamilMV\s*[-–]\s*", "", title).strip()

# ================= SCRAPER =================
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Opening homepage...")
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_timeout(5000)

    html = page.content()
    soup = BeautifulSoup(html, "lxml")

    # collect topics
    topics = []
    for a in soup.find_all("a", href=True):
        if "topic" in a["href"]:
            link = a["href"]
            if not link.startswith("http"):
                link = BASE_URL.rstrip("/") + link
            topics.append(link)

    topics = list(dict.fromkeys(topics))[:MAX_TOPICS]
    print("Topics:", len(topics))

    added = 0

    for url in topics:
        if added >= MAX_ITEMS:
            break

        try:
            print("Opening:", url)
            page.goto(url, timeout=60000)
            page.wait_for_timeout(4000)

            html = page.content()
            psoup = BeautifulSoup(html, "lxml")

            title_tag = psoup.title
            if not title_tag:
                continue

            title = clean_title(title_tag.get_text(strip=True))

            # extract magnets
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
                SubElement(item, "title").text = title
                SubElement(item, "link").text = magnet
                SubElement(item, "guid").text = magnet
                SubElement(item, "pubDate").text = datetime.utcnow().strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                )

                seen.add(magnet)
                added += 1
                print("ADDED:", title)

                if added >= MAX_ITEMS:
                    break

        except Exception as e:
            print("ERROR:", e)

    browser.close()

# ================= SAVE =================
ElementTree(rss).write(OUT_FILE, encoding="utf-8", xml_declaration=True)

with open(STATE_FILE, "w") as f:
    json.dump({"magnets": list(seen)}, f, indent=2)

print("DONE | Items:", added)
