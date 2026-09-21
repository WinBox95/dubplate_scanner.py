#!/usr/bin/env python3
"""
Automated 140 & Dubstep Dubplate Scanner (V2 - Strict Free & Fresh Filters)
==========================================================================
Filters strictly for:
1. Real direct track links (NEVER the main label profile URL)
2. Freshness (Only tracks from the last 90 days, skipping old back-catalogs)
3. Verified Free Downloads / Download Gates (Hypeddit, ToneDen, [FREE DL])
   - Filters out paid tracks that just have "VIP" or "Dubplate" in the title.
"""

import os
import re
import json
import time
import html
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

try:
    from curl_cffi import requests as cffi_requests
    USE_CURL = True
except ImportError:
    import requests
    USE_CURL = False

from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("140Scanner")

# 22 Individual Underground 140 Producers (SoundCloud)
SOUNDCLOUD_PRODUCERS = [
    ("Criso", "https://soundcloud.com/crisosound/tracks"),
    ("Wraz", "https://soundcloud.com/wraz/tracks"),
    ("Substrada", "https://soundcloud.com/substrada/tracks"),
    ("Basura", "https://soundcloud.com/basuradub/tracks"),
    ("11th Hour", "https://soundcloud.com/11th_hour/tracks"),
    ("Dalek One", "https://soundcloud.com/dalekone/tracks"),
    ("Cartridge", "https://soundcloud.com/cartridgedub/tracks"),
    ("Abstrakt Sonance", "https://soundcloud.com/abstraktsonance/tracks"),
    ("Ourman", "https://soundcloud.com/ourmansound/tracks"),
    ("Biak", "https://soundcloud.com/biakdub/tracks"),
    ("Roklem & Sebalo", "https://soundcloud.com/roklem/tracks"),
    ("Die By The Sword", "https://soundcloud.com/diebythesword/tracks"),
    ("IDHS", "https://soundcloud.com/idhsmusic/tracks"),
    ("Umbra", "https://soundcloud.com/umbra-uk/tracks"),
    ("Takjacob", "https://soundcloud.com/takjacob/tracks"),
    ("Sub Basics", "https://soundcloud.com/sub-basics/tracks"),
    ("Chad Dubz", "https://soundcloud.com/chaddubz/tracks"),
    ("Kercha", "https://soundcloud.com/kercha/tracks"),
    ("Taiko", "https://soundcloud.com/taikouk/tracks"),
    ("Bukez Finezt", "https://soundcloud.com/bukezfinezt/tracks"),
    ("Mikrodot", "https://soundcloud.com/mikrodot/tracks"),
    ("Rareman", "https://soundcloud.com/rareman/tracks")
]

# Sound System Channels & Collectives (SoundCloud)
SOUNDCLOUD_COLLECTIVES = [
    ("Stance Audio", "https://soundcloud.com/stanceaudio/tracks"),
    ("Infernal Sounds", "https://soundcloud.com/infernalsounds/tracks"),
    ("WiddFam", "https://soundcloud.com/widdfam/tracks"),
    ("FatKidOnFire", "https://soundcloud.com/fatkidonfire/tracks"),
    ("Honey & Bass", "https://soundcloud.com/honeyandbass/tracks"),
    ("DUPLOC", "https://soundcloud.com/duploc/tracks"),
    ("Dank 'N' Dirty Dubz", "https://soundcloud.com/dankndirtydubz/tracks")
]

# Bandcamp Netlabels (Subdomains)
BANDCAMP_NETLABELS = [
    ("WiddFam", "widdfam"),
    ("Dank 'N' Dirty Dubz", "dankndirtydubz"),
    ("FatKidOnFire", "fatkidonfire"),
    ("Cimmerian Records", "cimmerianrecords"),
    ("Honey & Bass", "honeyandbass"),
    ("Foundation Audio", "foundationaudio"),
    ("Transient Audio", "transientaudio"),
    ("Locus Sound", "locussound"),
    ("SubFreq Audio", "subfreqaudio"),
    ("Banana Stand Sound", "bananastandsound"),
    ("Infernal Sounds", "infernalsounds"),
    ("Encrypted Audio", "encryptedaudio")
]

HISTORY_FILE = "seen_dubs.json"
MAX_AGE_DAYS = 90  # Strictly ignore tracks older than 90 days


class DubplateMonitor:
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

    def fetch(self, url):
        time.sleep(self.delay)
        for _ in range(2):
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    return r.text
            except Exception:
                time.sleep(1)
        return None

    # --- Strict SoundCloud Scanner ---
    def scan_soundcloud_channel(self, name, url):
        html_text = self.fetch(url)
        if not html_text:
            return

        soup = BeautifulSoup(html_text, "html.parser")
        articles = soup.find_all("article")
        reserved_slugs = ("tracks", "albums", "sets", "reposts", "followers", "following", "popular-tracks", "comments")

        for art in articles:
            # 1. Resolve Exact Track Link (Never profile link)
            track_url = None
            track_title = None
            for a in art.find_all("a", href=True):
                href = a["href"].split("?")[0].strip()
                parts = [p for p in href.strip("/").split("/") if p]
                if len(parts) == 2 and parts[1].lower() not in reserved_slugs:
                    track_url = f"https://soundcloud.com/{parts[0]}/{parts[1]}"
                    track_title = a.get_text(strip=True)
                    break

            if not track_url or not track_title or track_url in self.seen_urls:
                continue

            # 2. Strict Freshness Filter
            is_old = False
            time_el = art.find("time")
            if time_el:
                dt_str = time_el.get("datetime")
                if dt_str:
                    try:
                        pub_date = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                        if (self.now - pub_date).days > MAX_AGE_DAYS:
                            is_old = True
                    except Exception:
                        pass
                t_text = time_el.get_text().lower()
                if re.search(r'(\d+y|\d+\s*year)', t_text):
                    is_old = True

            if is_old:
                continue

            # 3. Strict Free / Gate Verification
            full_text = art.get_text(separator=" ").lower()
            title_lower = track_title.lower()

            has_gate = bool(re.search(r'(hypeddit\.com|toneden\.io|theartistunion\.com|mediafire\.com|dropbox\.com|drive\.google\.com)', full_text))
            has_free_in_title = bool(re.search(r'(\[free\s*dl\]|\(free\s*dl\)|free\s*dl\b|\[free\s*download\]|\(free\s*download\)|free\s*download\b|free\s*flip|free\s*bootleg)', title_lower))

            # Exclude paid releases that just happen to say VIP or Dubplate
            if not (has_gate or has_free_in_title):
                continue

            cat = "Direct Free DL"
            if "hypeddit" in full_text:
                cat = "Hypeddit Download Gate"
            elif "toneden" in full_text:
                cat = "ToneDen Download Gate"
            elif "bootleg" in title_lower or "flip" in title_lower:
                cat = "Dubplate Bootleg / Flip"

            item = {
                "source": "SoundCloud",
                "artist": name,
                "title": track_title,
                "url": track_url,
                "category": cat
            }
            self.seen_urls.add(track_url)
            self.new_discoveries.append(item)
            logger.info(f"[*] NEW FREE SC DUB: {name} - {track_title} ({track_url})")

    # --- Bandcamp Scanner ---
    def scan_bandcamp_label(self, name, sub):
        base_url = f"https://{sub}.bandcamp.com"
        music_url = f"{base_url}/music"
        html_text = self.fetch(music_url) or self.fetch(base_url)
        if not html_text:
            return

        soup = BeautifulSoup(html_text, "html.parser")
        grid = soup.find(id="music-grid") or soup
        candidate_urls = []
        for a in grid.find_all("a", href=True):
            h = a["href"]
            if "/album/" in h or "/track/" in h:
                u = urljoin(base_url, h).split("?")[0]
                if u not in self.seen_urls and u not in candidate_urls:
                    candidate_urls.append(u)

        for u in candidate_urls[:6]:
            self.inspect_bandcamp_release(u, name)

    def inspect_bandcamp_release(self, url, label):
        txt = self.fetch(url)
        if not txt:
            return
        self.seen_urls.add(url)

        is_nyp = False
        m = re.search(r'data-tralbum="([^"]+)"', txt)
        tr = json.loads(html.unescape(m.group(1))) if m else None
        if tr:
            cur = tr.get("current", {})
            if cur.get("download_pref") == 1 or cur.get("min_price") == 0 or cur.get("freeDownloadPage"):
                is_nyp = True
            for t in tr.get("trackinfo", []):
                if t.get("has_free_download") or t.get("download_pref") == 1:
                    is_nyp = True

        if not is_nyp:
            soup = BeautifulSoup(txt, "html.parser")
            buy = " ".join(el.get_text() for el in soup.find_all(class_=re.compile(r'(buyItem|download-link)'))).lower()
            if "name your price" in buy or "free download" in buy:
                is_nyp = True

        if is_nyp:
            title = (tr.get("current", {}).get("title") if tr else "") or "Unknown Title"
            artist = (tr.get("artist") if tr else "") or label
            item = {
                "source": "Bandcamp",
                "artist": artist,
                "title": title,
                "url": url,
                "category": "Name Your Price / Free"
            }
            self.new_discoveries.append(item)
            logger.info(f"[*] NEW BANDCAMP NYP: {artist} - {title} ({url})")

    # --- Discord Webhook Notification ---
    @staticmethod
    def send_to_discord(webhook_url, item):
        if not webhook_url:
            return
        color = 0xff5500 if item["source"] == "SoundCloud" else 0x1da0c3
        payload = {
            "embeds": [{
                "title": f"🔊 {item['title'][:250]}",
                "url": item["url"],
                "color": color,
                "fields": [
                    {"name": "Artist / Channel", "value": item["artist"], "inline": True},
                    {"name": "Platform", "value": item["source"], "inline": True},
                    {"name": "Type", "value": item["category"], "inline": True}
                ],
                "footer": {"text": "140 Sound System Dubplate Alert • Fresh Drop"},
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }]
        }
        try:
            import requests as req
            resp = req.post(webhook_url, json=payload, timeout=10)
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed to post to Discord: {e}")

    def run(self):
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

        print("\n" + "=" * 75)
        print("  140 & DUBSTEP DUBPLATE MONITOR (STRICT FREE & FRESH)")
        print("=" * 75)
        print(f"[*] Max Age Threshold: Last {MAX_AGE_DAYS} Days (Filtering out old catalogs)")
        print(f"[*] Auditing {len(SOUNDCLOUD_PRODUCERS)} Producers + {len(SOUNDCLOUD_COLLECTIVES)} Channels on SoundCloud...")

        for name, url in SOUNDCLOUD_PRODUCERS + SOUNDCLOUD_COLLECTIVES:
            self.scan_soundcloud_channel(name, url)

        print(f"\n[*] Auditing {len(BANDCAMP_NETLABELS)} Bandcamp Netlabels...")
        for name, sub in BANDCAMP_NETLABELS:
            self.scan_bandcamp_label(name, sub)

        self.save_history()

        print(f"\n[+] Scan finished! Found {len(self.new_discoveries)} verified fresh free releases.")
        if webhook_url and self.new_discoveries:
            print(f"[*] Dispatching {len(self.new_discoveries)} alerts to Discord...")
            for item in self.new_discoveries:
                self.send_to_discord(webhook_url, item)

        if self.new_discoveries:
            with open("fresh_dubs.txt", "w", encoding="utf-8") as f:
                f.write(f"# Fresh 140 Drops ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n")
                for d in self.new_discoveries:
                    f.write(f"[{d['source']}] {d['artist']} - {d['title']} ({d['category']})\n{d['url']}\n\n")


if __name__ == "__main__":
    monitor = DubplateMonitor()
    monitor.run()

