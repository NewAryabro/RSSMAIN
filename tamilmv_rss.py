import time, json, os, re
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ================= CONFIG =================
BASE_URL = "https://www.1tamilmv.cymru/"
OUT_FILE = "tamilmv.xml"
STATE_FILE = "state.json"

MAX_TOPICS = 20
MAX_ITEMS = 25
MAX_STATE = 500

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
    title = re.sub(r"1TamilMV\s*[-–]\s*", "", title)
    return title.split("|")[0].strip()

# ================= SCRAPER =================
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    page = browser.new_page(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    )

    print("Opening homepage...")
    page.goto(BASE_URL, timeout=60000)
    page.wait_for_load_state("networkidle")

    html = page.content()
    soup = BeautifulSoup(html, "lxml")

    topics = []
    for a in soup.find_all("a", href=True):
        if "topic" in a["href"]:
            link = urljoin(BASE_URL, a["href"])
            topics.append(link)

    topics = list(set(topics))[:MAX_TOPICS]
    print("Topics:", len(topics))

    added = 0

    for url in topics:
        if added >= MAX_ITEMS:
            break

        try:
            print("Opening:", url)
            page.goto(url, timeout=60000)
            page.wait_for_load_state("networkidle")

            html = page.content()
            psoup = BeautifulSoup(html, "lxml")

            title_tag = psoup.title
            if not title_tag:
                continue

            title = clean_title(title_tag.get_text(strip=True))

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

# ================= SAVE XML =================
ElementTree(rss).write(OUT_FILE, encoding="utf-8", xml_declaration=True)

# ================= SAVE STATE =================
seen_list = list(seen)[-MAX_STATE:]

with open(STATE_FILE, "w") as f:
    json.dump({"magnets": seen_list}, f, indent=2)

print("DONE | Items:", added)
