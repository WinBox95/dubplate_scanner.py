#!/usr/bin/env python3
"""
Automated 140 & Dubstep Dubplate Scanner (Discord Webhook Edition)
=================================================================
Monitors 30+ underground 140 artists, sound system collectives, and netlabels
across SoundCloud and Bandcamp for free downloads, bootlegs, and NYP releases.
Sends instant rich embeds to a Discord channel via Webhook.

Works seamlessly with GitHub Actions on a recurring cron schedule.
"""

import os
import re
import json
import time
import html
import logging
from datetime import datetime
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

# Expanded Roster: 20 Individual 140 Producers
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


class DubplateMonitor:
    def __init__(self, delay=1.0):
        self.delay = delay
        self.seen_urls = self.load_history()
        self.new_discoveries = []

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

    # --- SoundCloud Scanner ---
    def scan_soundcloud_channel(self, name, url):
        html_text = self.fetch(url)
        if not html_text:
            return

        soup = BeautifulSoup(html_text, "html.parser")
        articles = soup.find_all("article")
        pat = r'(free\s*dl|free\s*download|freebie|bootleg|dubplate|flip|\bvip\b)'

        for art in articles:
            link_el = art.find("a", itemprop="url") or art.find("a", href=True)
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            full_url = f"https://soundcloud.com{href}" if href.startswith("/") else href

            if full_url in self.seen_urls:
                continue

            full_text = art.get_text(separator=" ")
            if re.search(pat, title, re.IGNORECASE) or re.search(pat, full_text, re.IGNORECASE):
                cat = "Direct Download / Freebie"
                if "hypeddit" in full_text.lower():
                    cat = "Hypeddit Download Gate"
                elif "toneden" in full_text.lower():
                    cat = "ToneDen Download Gate"
                elif "bootleg" in title.lower() or "flip" in title.lower():
                    cat = "Dubplate Flip / Bootleg"

                item = {
                    "source": "SoundCloud",
                    "artist": name,
                    "title": title,
                    "url": full_url,
                    "category": cat
                }
                self.seen_urls.add(full_url)
                self.new_discoveries.append(item)
                logger.info(f"[*] NEW SOUNDCLOUD DUB: {name} - {title}")

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
            logger.info(f"[*] NEW BANDCAMP NYP: {artist} - {title}")

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
                "footer": {"text": "140 Sound System Dubplate Alert"},
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }]
        }
        try:
            import requests as req
            resp = req.post(webhook_url, json=payload, timeout=10)
            if resp.status_code not in (200, 204):
                logger.warning(f"Discord webhook returned status {resp.status_code}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed to post to Discord: {e}")

    def run(self):
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

        print("\n" + "=" * 75)
        print("  140 & DUBSTEP DUBPLATE MONITOR (DISCORD NOTIFIER)")
        print("=" * 75)
        print(f"[*] Webhook configured: {'YES' if webhook_url else 'NO (Local Only)'}")
        print(f"[*] Auditing {len(SOUNDCLOUD_PRODUCERS)} Producers + {len(SOUNDCLOUD_COLLECTIVES)} SC Channels...")

        for name, url in SOUNDCLOUD_PRODUCERS + SOUNDCLOUD_COLLECTIVES:
            self.scan_soundcloud_channel(name, url)

        print(f"\n[*] Auditing {len(BANDCAMP_NETLABELS)} Bandcamp Netlabels...")
        for name, sub in BANDCAMP_NETLABELS:
            self.scan_bandcamp_label(name, sub)

        self.save_history()

        print(f"\n[+] Scan finished! Found {len(self.new_discoveries)} new releases.")
        if webhook_url and self.new_discoveries:
            print(f"[*] Dispatching {len(self.new_discoveries)} alerts to Discord...")
            for item in self.new_discoveries:
                self.send_to_discord(webhook_url, item)

        # Output local text summary
        if self.new_discoveries:
            with open("fresh_dubs.txt", "w", encoding="utf-8") as f:
                f.write(f"# Fresh 140 Drops ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n")
                for d in self.new_discoveries:
                    f.write(f"[{d['source']}] {d['artist']} - {d['title']} ({d['category']})\n{d['url']}\n\n")


if __name__ == "__main__":
    monitor = DubplateMonitor()
    monitor.run()

