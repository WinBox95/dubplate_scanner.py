#!/usr/bin/env python3
"""
Deep-Digging 140 & Dubstep Free Dubplate Scanner (V5 - Expanded Search Depth)
============================================================================
Pulls deeper batches of unreleased dubplates, bootlegs, edits, and NYP releases
by expanding query variety and searching 50+ results per query.
"""

import os
import re
import json
import time
import html
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin, quote_plus

try:
    from curl_cffi import requests as cffi_requests
    USE_CURL = True
except ImportError:
    import requests
    USE_CURL = False

from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("140DeepScanner")

# Expanded 16-Query Arsenal covering all 140 sub-genres and dub styles
SC_TAG_QUERIES = [
    '140 "free dl"',
    'deep dubstep "free dl"',
    '140 dubplate "free dl"',
    '140 bootleg "free dl"',
    '140 flip "free dl"',
    '140 edit "free dl"',
    '140 dubpack "free"',
    'sound system music "free dl"',
    'deep 140 roller "free dl"',
    '140 grime "free dl"',
    '140 "free download"',
    'deep dubstep "free download"',
    '140 dubplate free',
    'minimal dubstep "free dl"',
    '140 vip "free dl"',
    'sound system dub "free dl"'
]

# Expanded Bandcamp Tag Discovery Hubs
BC_TAG_HUBS = [
    "https://bandcamp.com/tag/140",
    "https://bandcamp.com/tag/deep-dubstep",
    "https://bandcamp.com/tag/sound-system-music",
    "https://bandcamp.com/tag/140-bpm",
    "https://bandcamp.com/tag/dubplate"
]

HISTORY_FILE = "seen_dubs.json"
MAX_AGE_DAYS = 60  # Generous 2-month window for deep dubs

FALLBACK_CLIENT_IDS = [
    "iZIs9mchVcX5lhVR1EzGCcyEVAazo9J4",
    "b77c5d01217e949ff6a9926a793a8d79",
    "2t9loNfh0ekOfbnFeO3wEiHGMIVk3o28"
]


class DeepTagScanner:
    def __init__(self, delay=1.0):
        self.delay = delay
        self.seen_urls = self.load_history()
        self.new_discoveries = []
        self.now = datetime.now(timezone.utc)

        if USE_CURL:
            logger.info("Using curl_cffi Chrome TLS impersonation.")
            self.session = cffi_requests.Session(impersonate="chrome120")
        else:
            self.session = requests.Session()
            self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

        self.sc_client_id = self.get_soundcloud_client_id()

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                pass
        return set()

    def save_history(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(self.seen_urls), f, indent=2)

    def get_soundcloud_client_id(self):
        try:
            resp = self.session.get("https://soundcloud.com", timeout=10)
            if resp.status_code == 200:
                scripts = re.findall(r'src="(https://a-v2\.sndcdn\.com/assets/[^"]+\.js)"', resp.text)
                for s_url in scripts[-4:]:
                    s_resp = self.session.get(s_url, timeout=10)
                    m = re.search(r'client_id[:=]["\']([a-zA-Z0-9]{32})["\']', s_resp.text)
                    if m:
                        return m.group(1)
        except Exception:
            pass
        return FALLBACK_CLIENT_IDS[0]

    def search_soundcloud_tags(self, query, limit=50):
        logger.info(f"Searching SoundCloud: '{query}' (Depth: {limit})")
        search_url = f"https://api-v2.soundcloud.com/search/tracks?q={quote_plus(query)}&client_id={self.sc_client_id}&limit={limit}&access=playable"

        time.sleep(self.delay)
        try:
            resp = self.session.get(search_url, timeout=15)
            if resp.status_code != 200:
                return
            tracks = resp.json().get("collection", [])
        except Exception:
            return

        for tr in tracks:
            permalink = tr.get("permalink_url", "")
            title = tr.get("title", "")
            if not permalink or not title or permalink in self.seen_urls:
                continue

            created_at = tr.get("created_at")
            if created_at:
                try:
                    pub = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if (self.now - pub).days > MAX_AGE_DAYS:
                        continue
                except Exception:
                    pass

            purchase_url = tr.get("purchase_url") or ""
            desc = tr.get("description") or ""
            comb = f"{title} {desc} {purchase_url}".lower()

            if any(term in comb for term in ["vinyl", "pre-order", "preorder", "12\"", "cassette"]):
                continue

            downloadable = tr.get("downloadable", False)
            has_gate = bool(re.search(r'(hypeddit\.com|toneden\.io|theartistunion\.com|mediafire\.com|dropbox\.com)', comb))
            has_free_title = bool(re.search(r'(\[free\s*dl\]|\(free\s*dl\)|free\s*dl\b|\[free\s*download\]|\(free\s*download\)|free\s*download\b|free\s*flip|free\s*bootleg|free\s*edit|dubpack)', title.lower()))

            if not (downloadable or has_gate or has_free_title):
                continue

            artist = tr.get("user", {}).get("username", "Underground Producer")
            cat = "Direct Free Download"
            if "hypeddit" in comb:
                cat = "Hypeddit Download Gate"
            elif "toneden" in comb:
                cat = "ToneDen Download Gate"
            elif "bootleg" in title.lower() or "flip" in title.lower() or "edit" in title.lower():
                cat = "Dubplate Edit / Bootleg"
            elif "dubpack" in title.lower():
                cat = "Free 140 Dubpack"

            item = {
                "source": "SoundCloud",
                "artist": artist,
                "title": title,
                "url": permalink,
                "category": cat,
                "dl_gate": purchase_url if has_gate else permalink
            }
            self.seen_urls.add(permalink)
            self.new_discoveries.append(item)
            logger.info(f"[*] NEW DEEP DUB: {artist} - {title}")

    def search_bandcamp_tags(self, hub_url):
        logger.info(f"Auditing Bandcamp Tag Hub: {hub_url}")
        time.sleep(self.delay)
        try:
            resp = self.session.get(hub_url, timeout=15)
            if resp.status_code != 200:
                return
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception:
            return

        candidate_urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ("/album/" in href or "/track/" in href) and ".bandcamp.com" in href:
                clean = href.split("?")[0]
                if clean not in self.seen_urls and clean not in candidate_urls:
                    candidate_urls.append(clean)

        for u in candidate_urls[:12]:
            self.inspect_bandcamp_release(u)

    def inspect_bandcamp_release(self, url):
        time.sleep(self.delay)
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return
            txt = resp.text
        except Exception:
            return
        self.seen_urls.add(url)

        if any(term in url.lower() for term in ["vinyl", "preorder", "pre-order"]):
            return

        is_nyp = False
        m = re.search(r'data-tralbum="([^"]+)"', txt)
        tr = json.loads(html.unescape(m.group(1))) if m else None

        pub_date = None
        if tr:
            cur = tr.get("current", {})
            raw_date = cur.get("publish_date") or cur.get("release_date")
            if raw_date:
                try:
                    clean_d = re.sub(r'\s+[A-Z]{3,4}$', '', raw_date).strip()
                    pub_date = datetime.strptime(clean_d[:20].strip(), "%d %b %Y %H:%M:%S")
                except Exception:
                    pass

        if not pub_date:
            m_date = re.search(r'itemprop="datePublished"\s+content="([^"]+)"', txt)
            if m_date:
                try:
                    pub_date = datetime.fromisoformat(m_date.group(1).split("T")[0])
                except Exception:
                    pass

        if pub_date and (datetime.now() - pub_date).days > MAX_AGE_DAYS:
            return

        if tr:
            cur = tr.get("current", {})
            title = cur.get("title", "")
            if any(neg in title.lower() for neg in ["vinyl", "pre-order", "preorder", "12\"", "cassette"]):
                return
            if cur.get("download_pref") == 1 or cur.get("min_price") == 0 or cur.get("freeDownloadPage"):
                is_nyp = True
            for t in tr.get("trackinfo", []):
                if t.get("has_free_download") or t.get("download_pref") == 1:
                    is_nyp = True

        if not is_nyp:
            soup = BeautifulSoup(txt, "html.parser")
            buy = " ".join(el.get_text() for el in soup.find_all(class_=re.compile(r'(buyItem|download-link)'))).lower()
            if ("name your price" in buy or "free download" in buy) and not any(term in buy for term in ["vinyl", "pre-order", "preorder"]):
                is_nyp = True

        if is_nyp:
            title = (tr.get("current", {}).get("title") if tr else "") or "Unknown Title"
            artist = (tr.get("artist") if tr else "") or "Underground Artist"
            item = {
                "source": "Bandcamp",
                "artist": artist,
                "title": title,
                "url": url,
                "category": "Name Your Price / Free",
                "dl_gate": url
            }
            self.new_discoveries.append(item)
            logger.info(f"[*] NEW BANDCAMP NYP: {artist} - {title}")

    @staticmethod
    def send_to_discord(webhook_url, payload):
        if not webhook_url:
            return
        try:
            import requests as req
            req.post(webhook_url, json=payload, timeout=10)
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed to post to Discord: {e}")

    def run(self):
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
        is_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

        print("\n" + "=" * 75)
        print("  DEEP-DIGGING 140 DUBPLATE & NYP DISCOVERY (GLOBAL)")
        print("=" * 75)
        print(f"[*] Search Scope: 16 Global Queries x 50 Results Deep")
        print(f"[*] Freshness Limit: Past {MAX_AGE_DAYS} Days")

        for q in SC_TAG_QUERIES:
            self.search_soundcloud_tags(q, limit=50)

        for hub in BC_TAG_HUBS:
            self.search_bandcamp_tags(hub)

        self.save_history()

        print(f"\n[+] Scan finished! Discovered {len(self.new_discoveries)} new 140 dubs.")

        if webhook_url:
            if self.new_discoveries:
                print(f"[*] Dispatching {len(self.new_discoveries)} new releases to Discord...")
                for item in self.new_discoveries:
                    color = 0xff5500 if item["source"] == "SoundCloud" else 0x1da0c3
                    fields = [
                        {"name": "Artist", "value": item["artist"][:100], "inline": True},
                        {"name": "Platform", "value": item["source"], "inline": True},
                        {"name": "Category", "value": item["category"], "inline": True}
                    ]
                    if item.get("dl_gate") and item["dl_gate"] != item["url"]:
                        fields.append({"name": "Download Gate", "value": f"[Direct Download]({item['dl_gate']})", "inline": False})

                    payload = {
                        "embeds": [{
                            "title": f"🔊 {item['title'][:250]}",
                            "url": item["url"],
                            "color": color,
                            "fields": fields,
                            "footer": {"text": "140 Dubplate Discovery • Fresh Free Drop"},
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }]
                    }
                    self.send_to_discord(webhook_url, payload)
            elif is_manual:
                print("[*] Sending manual check status to Discord...")
                status = {
                    "embeds": [{
                        "title": "🟢 140 Dubplate Scanner: Deep Scan Active",
                        "description": "Scanned 16 queries at 50-track depth.\n\n**Result:** No new unreleased dubplates beyond what is already in your feed.\n*Monitoring for the next upload.*",
                        "color": 0x2ecc71,
                        "footer": {"text": "Automated schedule active every 6 hours"},
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }]
                }
                self.send_to_discord(webhook_url, status)


if __name__ == "__main__":
    scanner = DeepTagScanner()
    scanner.run()
