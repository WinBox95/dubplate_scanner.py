#!/usr/bin/env python3
"""
Hybrid 140 Dubplate Scanner (Strict Anti-House & Dubstep Lockdown Edition)
==========================================================================
Eliminates 140 BPM Speed House, Bass House, 4x4, and Tech House edits by:
1. Tethering all search queries strictly to 'dubstep', 'sound system', & 'dubplate'
2. Inspecting SoundCloud's genre & tag_list with a strict House blocklist
3. Maintaining direct feeds for 37 Sound System culture pillars
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
logger = logging.getLogger("140LockdownScanner")

# 37 PILLARS OF SOUND SYSTEM CULTURE (DIRECT FEEDS)
PILLAR_SOUNDCLOUD = [
    ("Ternion Sound", "https://soundcloud.com/ternionsound/tracks"),
    ("The Widdler", "https://soundcloud.com/the_widdler/tracks"),
    ("Distinct Motive", "https://soundcloud.com/distinctmotive/tracks"),
    ("Chef Boyarbeatz", "https://soundcloud.com/chef_boyarbeatz/tracks"),
    ("Alix Perez", "https://soundcloud.com/alixperez/tracks"),
    ("Hamdi", "https://soundcloud.com/hamdimusic/tracks"),
    ("Truth", "https://soundcloud.com/truthdubstep/tracks"),
    ("Deep Dark and Dangerous", "https://soundcloud.com/deepdarkanddangerous/tracks"),
    ("Khiva", "https://soundcloud.com/khiva/tracks"),
    ("Pushloop", "https://soundcloud.com/pushloop/tracks"),
    ("Bukez Finezt", "https://soundcloud.com/bukezfinezt/tracks"),
    ("Commodo", "https://soundcloud.com/commodo/tracks"),
    ("Sir Hiss", "https://soundcloud.com/sirhiss/tracks"),
    ("Drone", "https://soundcloud.com/dronemusic/tracks"),
    ("Sleeper", "https://soundcloud.com/sleeper/tracks"),
    ("J:Kenzo", "https://soundcloud.com/jkenzo/tracks"),
    ("Chad Dubz", "https://soundcloud.com/chaddubz/tracks"),
    ("Kercha", "https://soundcloud.com/kercha/tracks"),
    ("Taiko", "https://soundcloud.com/taikouk/tracks"),
    ("Enigma Dubz", "https://soundcloud.com/enigmadubz/tracks"),
    ("Mikrodot", "https://soundcloud.com/mikrodot/tracks"),
    ("Cimm", "https://soundcloud.com/cimm/tracks"),
    ("Sepia", "https://soundcloud.com/sepia/tracks"),
    ("Cartridge", "https://soundcloud.com/cartridgedub/tracks"),
    ("Wraz", "https://soundcloud.com/wraz/tracks"),
    ("Criso", "https://soundcloud.com/crisosound/tracks"),
    ("Dalek One", "https://soundcloud.com/dalekone/tracks"),
    ("Basura", "https://soundcloud.com/basuradub/tracks"),
    ("11th Hour", "https://soundcloud.com/11th_hour/tracks"),
    ("Sub Basics", "https://soundcloud.com/sub-basics/tracks"),
    ("Stance Audio", "https://soundcloud.com/stanceaudio/tracks"),
    ("Infernal Sounds", "https://soundcloud.com/infernalsounds/tracks"),
    ("WiddFam", "https://soundcloud.com/widdfam/tracks"),
    ("FatKidOnFire", "https://soundcloud.com/fatkidonfire/tracks"),
    ("Honey & Bass", "https://soundcloud.com/honeyandbass/tracks"),
    ("DUPLOC", "https://soundcloud.com/duploc/tracks"),
    ("Dank 'N' Dirty Dubz", "https://soundcloud.com/dankndirtydubz/tracks")
]

PILLAR_BANDCAMP = [
    ("Ternion Sound", "ternionsound"),
    ("The Widdler", "the-widdler"),
    ("Chef Boyarbeatz", "chefboyarbeatz"),
    ("Distinct Motive", "distinctmotive"),
    ("Hamdi", "hamdimusic"),
    ("Truth", "truthdubstep"),
    ("Deep Dark and Dangerous", "deepdarkanddangerous"),
    ("Khiva", "khiva"),
    ("Pushloop", "pushloop"),
    ("Bukez Finezt", "bukezfinezt"),
    ("Alix Perez", "alixperez"),
    ("Sleeper", "sleeper"),
    ("J:Kenzo", "jkenzo"),
    ("Chad Dubz", "chaddubz"),
    ("Kercha", "kercha"),
    ("Taiko", "taikouk"),
    ("DUPLOC", "duploc"),
    ("White Peach Records", "whitepeachrecords"),
    ("Infernal Sounds", "infernalsounds"),
    ("WiddFam", "widdfam"),
    ("FatKidOnFire", "fatkidonfire"),
    ("Dank 'N' Dirty Dubz", "dankndirtydubz"),
    ("Cimmerian Records", "cimmerianrecords"),
    ("Honey & Bass", "honeyandbass"),
    ("Foundation Audio", "foundationaudio")
]

# TIGHTENED DUBSTEP-LOCKED QUERIES
SC_TAG_QUERIES = [
    '140 dubstep "free dl"',
    'deep dubstep "free dl"',
    '140 dubplate "free dl"',
    '140 dubstep bootleg "free dl"',
    '140 dubstep flip "free dl"',
    '140 dubstep edit "free dl"',
    '140 dubpack "free"',
    'sound system dubstep "free dl"',
    'deep 140 roller "free dl"',
    '140 dubstep "free download"',
    'deep dubstep "free download"',
    '140 dubplate free download',
    'minimal dubstep "free dl"',
    '140 dubstep vip "free dl"',
    'sound system dub "free dl"'
]

BC_TAG_HUBS = [
    "https://bandcamp.com/tag/140",
    "https://bandcamp.com/tag/deep-dubstep",
    "https://bandcamp.com/tag/sound-system-music",
    "https://bandcamp.com/tag/140-bpm",
    "https://bandcamp.com/tag/dubplate"
]

HISTORY_FILE = "seen_dubs.json"
MAX_AGE_DAYS = 60

# STRICT OFF-GENRE & MERCH BLOCKLISTS
HOUSE_DISQUALIFIERS = [
    r'\bhouse\b', r'\btech\s*house\b', r'\bbass\s*house\b', r'\bdeep\s*house\b',
    r'\bspeed\s*house\b', r'\bstutter\s*house\b', r'\bafro\s*house\b', r'\belectro\s*house\b',
    r'\bg-house\b', r'\b4x4\b', r'\bspeed\s*garage\b', r'\btechno\b', r'\btrance\b',
    r'\bamapiano\b', r'\bhardstyle\b', r'\bpsytrance\b'
]

MERCH_BLOCKLIST = [
    "vinyl", "pre-order", "preorder", "pre order", "12\"", "7\"",
    "lathe cut", "cassette", "tape", "merch", "t-shirt", "hoodie",
    "shipping", "buy now", "out now on", "forthcoming on"
]

FALLBACK_CLIENT_IDS = [
    "iZIs9mchVcX5lhVR1EzGCcyEVAazo9J4",
    "b77c5d01217e949ff6a9926a793a8d79",
    "2t9loNfh0ekOfbnFeO3wEiHGMIVk3o28"
]


class LockdownScanner:
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

    @staticmethod
    def is_off_genre(title, genre, tag_list, description):
        combined = f"{title} {genre} {tag_list} {description}".lower()
        for pat in HOUSE_DISQUALIFIERS:
            if re.search(pat, combined):
                return True
        return False

    def is_pillar_artist(self, artist_name, url):
        combined = f"{artist_name} {url}".lower()
        for name, _ in PILLAR_SOUNDCLOUD + [(n, f"https://{s}.bandcamp.com") for n, s in PILLAR_BANDCAMP]:
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
            if clean_name in re.sub(r'[^a-zA-Z0-9]', '', combined):
                return True, name
        return False, artist_name

    def scan_soundcloud_channel(self, name, url):
        time.sleep(self.delay)
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code != 200:
                return
            raw_html = r.text
        except Exception:
            return

        soup = BeautifulSoup(raw_html, "html.parser")
        articles = soup.find_all("article")
        reserved = ("tracks", "albums", "sets", "reposts", "followers", "following", "popular-tracks", "comments")

        for art in articles:
            track_url = None
            track_title = None
            for a in art.find_all("a", href=True):
                href = a["href"].split("?")[0].strip()
                parts = [p for p in href.strip("/").split("/") if p]
                if len(parts) == 2 and parts[1].lower() not in reserved:
                    track_url = f"https://soundcloud.com/{parts[0]}/{parts[1]}"
                    track_title = a.get_text(strip=True)
                    break

            if not track_url or not track_title or track_url in self.seen_urls:
                continue

            full_text = art.get_text(separator=" ").lower()
            title_lower = track_title.lower()

            if any(term in title_lower for term in ["vinyl", "pre-order", "preorder", "12\"", "cassette"]):
                continue

            if self.is_off_genre(track_title, "", "", full_text):
                continue

            is_old = False
            time_el = art.find("time")
            if time_el:
                dt_str = time_el.get("datetime")
                if dt_str:
                    try:
                        pub = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                        if (self.now - pub).days > MAX_AGE_DAYS:
                            is_old = True
                    except Exception:
                        pass
                t_text = time_el.get_text().lower()
                if re.search(r'(\d+\s*year|\d+y\b)', t_text):
                    is_old = True
                m = re.search(r'(\d+)\s*month', t_text)
                if m and int(m.group(1)) > 2:
                    is_old = True

            if is_old:
                continue

            has_gate = bool(re.search(r'(hypeddit\.com|toneden\.io|theartistunion\.com|mediafire\.com|dropbox\.com)', full_text))
            has_free_title = bool(re.search(r'(\[free\s*dl\]|\(free\s*dl\)|free\s*dl\b|\[free\s*download\]|\(free\s*download\)|free\s*download\b|free\s*flip|free\s*bootleg|free\s*vip|free\s*edit)', title_lower))

            if not (has_gate or has_free_title):
                continue

            cat = "Direct Free Download"
            if "hypeddit" in full_text:
                cat = "Hypeddit Download Gate"
            elif "toneden" in full_text:
                cat = "ToneDen Download Gate"
            elif "bootleg" in title_lower or "flip" in title_lower or "edit" in title_lower:
                cat = "Dubplate Edit / Bootleg"

            item = {
                "source": "SoundCloud",
                "artist": name,
                "title": track_title,
                "url": track_url,
                "category": cat,
                "tier": f"👑 Pillar Drop • {name}",
                "dl_gate": track_url
            }
            self.seen_urls.add(track_url)
            self.new_discoveries.append(item)
            logger.info(f"[*] 👑 PILLAR SC DROP: {name} - {track_title}")

    def search_soundcloud_tags(self, query, limit=40):
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

            genre = tr.get("genre") or ""
            tag_list = tr.get("tag_list") or ""
            desc = tr.get("description") or ""

            # STRICT HOUSE & 4X4 BLOCKLIST
            if self.is_off_genre(title, genre, tag_list, desc):
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
            comb = f"{title} {desc} {purchase_url}".lower()

            if any(term in comb for term in ["vinyl", "pre-order", "preorder", "12\"", "cassette"]):
                continue

            downloadable = tr.get("downloadable", False)
            has_gate = bool(re.search(r'(hypeddit\.com|toneden\.io|theartistunion\.com|mediafire\.com|dropbox\.com)', comb))
            has_free_title = bool(re.search(r'(\[free\s*dl\]|\(free\s*dl\)|free\s*dl\b|\[free\s*download\]|\(free\s*download\)|free\s*download\b|free\s*flip|free\s*bootleg|free\s*edit|dubpack)', title.lower()))

            if not (downloadable or has_gate or has_free_title):
                continue

            raw_artist = tr.get("user", {}).get("username", "Underground Producer")
            is_pillar, pillar_name = self.is_pillar_artist(raw_artist, permalink)
            tier_label = f"👑 Pillar Drop • {pillar_name}" if is_pillar else f"🌐 Underground Discovery • {raw_artist}"

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
                "artist": raw_artist,
                "title": title,
                "url": permalink,
                "category": cat,
                "tier": tier_label,
                "dl_gate": purchase_url if has_gate else permalink
            }
            self.seen_urls.add(permalink)
            self.new_discoveries.append(item)
            logger.info(f"[*] NEW DUBSTEP DUB: {raw_artist} - {title}")

    def scan_bandcamp_discog(self, name, sub, limit=6):
        base_url = f"https://{sub}.bandcamp.com"
        time.sleep(self.delay)
        try:
            r = self.session.get(f"{base_url}/music", timeout=15)
            if r.status_code != 200:
                r = self.session.get(base_url, timeout=15)
            if r.status_code != 200:
                return
            txt = r.text
        except Exception:
            return

        soup = BeautifulSoup(txt, "html.parser")
        grid = soup.find(id="music-grid") or soup
        candidate_urls = []
        for a in grid.find_all("a", href=True):
            h = a["href"]
            if "/album/" in h or "/track/" in h:
                u = urljoin(base_url, h).split("?")[0]
                if u not in self.seen_urls and u not in candidate_urls:
                    candidate_urls.append(u)

        for u in candidate_urls[:limit]:
            self.inspect_bandcamp_release(u, name, is_pillar_source=True)

    def search_bandcamp_tags(self, hub_url):
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

        for u in candidate_urls[:10]:
            self.inspect_bandcamp_release(u, "Underground Artist", is_pillar_source=False)

    def inspect_bandcamp_release(self, url, label, is_pillar_source=False):
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
            artist = (tr.get("artist") if tr else "") or label
            is_pillar, pillar_name = self.is_pillar_artist(artist, url)
            tier_label = f"👑 Pillar Drop • {pillar_name}" if (is_pillar or is_pillar_source) else f"🌐 Underground Discovery • {artist}"

            item = {
                "source": "Bandcamp",
                "artist": artist,
                "title": title,
                "url": url,
                "category": "Name Your Price / Free",
                "tier": tier_label,
                "dl_gate": url
            }
            self.new_discoveries.append(item)
            logger.info(f"[*] NEW BANDCAMP NYP: {artist} - {title} ({url})")

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

        print("\n" + "=" * 78)
        print("  140 DUBSTEP & SOUND SYSTEM MONITOR (ANTI-HOUSE STRICT LOCKDOWN)")
        print("=" * 78)

        # 1. Audit Pillar Artists on SoundCloud
        print(f"[*] Auditing {len(PILLAR_SOUNDCLOUD)} Sound System Pillars on SoundCloud...")
        for name, url in PILLAR_SOUNDCLOUD:
            self.scan_soundcloud_channel(name, url)

        # 2. Audit Pillar Netlabels on Bandcamp
        print(f"[*] Auditing {len(PILLAR_BANDCAMP)} Pillar Imprints on Bandcamp...")
        for name, sub in PILLAR_BANDCAMP:
            self.scan_bandcamp_discog(name, sub)

        # 3. Dubstep-Locked Tag Harvest
        print(f"[*] Running Dubstep-Locked Tag Harvest ({len(SC_TAG_QUERIES)} queries x 40 depth)...")
        for q in SC_TAG_QUERIES:
            self.search_soundcloud_tags(q, limit=40)

        for hub in BC_TAG_HUBS:
            self.search_bandcamp_tags(hub)

        self.save_history()

        print(f"\n[+] Scan finished! Found {len(self.new_discoveries)} legit 140 dubstep releases.")

        if webhook_url:
            if self.new_discoveries:
                print(f"[*] Dispatching {len(self.new_discoveries)} alerts to Discord...")
                for item in self.new_discoveries:
                    color = 0xffd700 if "👑" in item["tier"] else (0xff5500 if item["source"] == "SoundCloud" else 0x1da0c3)
                    fields = [
                        {"name": "Tier / Category", "value": item["tier"], "inline": False},
                        {"name": "Platform", "value": item["source"], "inline": True},
                        {"name": "Download Type", "value": item["category"], "inline": True}
                    ]
                    if item.get("dl_gate") and item["dl_gate"] != item["url"]:
                        fields.append({"name": "Direct Download Gate", "value": f"[Get Track via Hypeddit / ToneDen]({item['dl_gate']})", "inline": False})

                    payload = {
                        "embeds": [{
                            "title": f"🔊 {item['title'][:250]}",
                            "url": item["url"],
                            "color": color,
                            "fields": fields,
                            "footer": {"text": "140 Dubstep & Sound System Monitor"},
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }]
                    }
                    self.send_to_discord(webhook_url, payload)
            elif is_manual:
                print("[*] Sending manual check status to Discord...")
                status = {
                    "embeds": [{
                        "title": "🟢 140 Dubplate Monitor: Fully Synced (Anti-House Active)",
                        "description": f"Audited **{len(PILLAR_SOUNDCLOUD)} Pillar Artists** + **Dubstep Tag Sweep**.\n\n**Status:** No brand-new unreleased dubs beyond your current feed.\n*Monitoring for fresh drops.*",
                        "color": 0x2ecc71,
                        "footer": {"text": "Automated schedule active every 6 hours"},
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }]
                }
                self.send_to_discord(webhook_url, status)


if __name__ == "__main__":
    scanner = LockdownScanner()
    scanner.run()
