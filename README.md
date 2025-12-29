# 1TamilMV Torrent RSS (Experimental)

⚠️ This project is experimental and may break anytime.

## What it does
- Scrapes 1TamilMV homepage
- Opens forum posts
- Extracts torrent / magnet links
- Generates RSS feed for auto-leech bots

## Files
- tamilmv_rss.py → main scraper
- tamilmv.xml → generated RSS
- state.json → avoids duplicates
- rss.yml → GitHub Actions workflow

## GitHub Pages
Enable Pages from:
Settings → Pages → Branch: main → /root

RSS URL:
https://YOURNAME.github.io/YOURREPO/tamilmv.xml

## Warning
- Cloudflare protection may block requests
- GitHub Actions IPs are not stable
- Telegram source is more reliable
