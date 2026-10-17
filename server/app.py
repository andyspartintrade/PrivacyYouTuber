"""Τοπικός HTTP server — δέχεται watch events ΚΑΙ σερβίρει το web dashboard.

Μόνο Python stdlib (http.server). Δεν υπάρχει τίποτα να κάνεις pip install.

Endpoints:
    POST /watch              ← το extension στέλνει εδώ το metadata του βίντεο
    GET  /                   ← το dashboard (web UI)
    GET  /api/dashboard      ← stats + topics + videos (χωρίς δίκτυο)
    GET  /api/suggest?q=...  ← ανώνυμες προτάσεις αναζήτησης (χτυπάει δίκτυο)
    GET  /health             ← έλεγχος ότι ο server ζει
    OPTIONS /watch           ← CORS preflight
"""

import json
import os
import re
import sys
import threading
import traceback
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# 🪟 Στο Windows, κάθε subprocess από windowed .exe (--noconsole) ΞΑΝΑΑΝΟΙΓΕΙ
#    παράθυρο κονσόλας (flash) — ακόμα κι αν η εφαρμογή δεν έχει κονσόλα.
#    Το CREATE_NO_WINDOW το κρύβει εντελώς. Ορίζεται άπαξ, εδώ, με ασφάλεια.
_NO_WINDOW = getattr(__import__("subprocess"), "CREATE_NO_WINDOW", 0x08000000)

from datetime import datetime
from . import db, recommender

PORT = 8765
HOST = "127.0.0.1"  # δέχεται ΜΟΝΟ τοπικές συνδέσεις — ποτέ από το internet

# 📦 Η τρέχουσα έκδοση του app. Το auto-update τη συγκρίνει με το latest.json.
VERSION = "1.4.4"

# 📦 Πού ψάχνει το app για ενημερώσεις (GitHub raw). Public repo απαραίτητο.
UPDATE_URL = "https://raw.githubusercontent.com/andyspartintrade/PrivacyYouTuber/main/latest.json"

# 🔑 LICENSING — Gumroad license keys (δωρεάν feature, online verify).
#    Ο χρήστης ενεργοποιεί ΜΙΑ φορά (online) με το key που πήρε στην αγορά του.
#    Η εφαρμογή ξανατσεκάρει σιωπηλά κάθε LICENSE_RECHECK_DAYS μέρες.
#    Όριο ενεργοποιήσεων ανά key = LICENSE_MAX_USES (κόβει το forum-leak).
GUMROAD_VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify"

# 🔑 Hardcoded product_id — ΔΕΝ είναι secret (φαίνεται στο product URL).
#    Χρειάζεται για το license verify ώστε ο ΠΕΛΑΤΗΣ να μη χρειάζεται .env.
#    Το .env (αν υπάρχει) έχει προτεραιότητα — για dev/testing.
GUMROAD_PRODUCT_ID_DEFAULT = "sOap88TaNJAKelU4sjM4IQ=="
LICENSE_RECHECK_DAYS = 3          # κάθε 3 μέρες σιωπηλός επανέλεγχος
LICENSE_MAX_USES = 5              # πάνω από 5 ενεργοποιήσεις = leak/μη νόμιμο
# 🔌 Fail-OPEN για ενεργοποιημένους: αν το Gumroad δεν απαντήσει (offline/
#    downtime/404), ο χρήστης που ενεργοποιήθηκε ποτέ τοπικά ΜΠΑΙΝΕΙ ΚΑΝΟΝΙΚΑ
#    — χωρίς όριο αποτυχιών. Hard-lock ΜΟΝΟ σε ρητό refund/dispute/uses>MAX.
#    (Μην ξαναβάλεις όριο εδώ: κλειδώνει τίμιο πελάτη σε πτώση δικτύου.)

# ⚠️ Ο τίμιος ανοίγει την εφαρμογή ΠΟΛΛΕΣ φορές → το check ΔΕΝ πρέπει να ανεβάζει
#    το uses. ΜΟΝΟ η πρώτη ενεργοποίηση ανεβάζει (increment_uses_count=true).
#    Όλα τα recheck κάνουν increment_uses_count=false.


# 🔐 Secrets: φορτώνονται από το .env (ΠΟΤΕ hardcoded, ΠΟΤΕ στο git).
def _env_candidates():
    """Πιθανές θέσεις του .env — σειρά προτεραιότητας:
    1. Δίπλα στο .exe (PyInstaller onefile: sys.executable) ή στον φάκελο app.
    2. Το τρέχον working directory.
    3. Το project root (source layout)."""
    cands = []
    exe_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False) else None
    if exe_dir:
        cands.append(os.path.join(exe_dir, ".env"))
    cands.append(os.path.join(os.getcwd(), ".env"))
    cands.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    return cands


def _load_env():
    """Φορτώνει KEY=VALUE από το .env (stdlib-only, χωρίς python-dotenv).
    Γραμμές που ξεκινούν με # ή είναι κενές → αγνοούνται."""
    env = {}
    for path in _env_candidates():
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
            break  # βρήκαμε το πρώτο υπαρκτό .env
        except OSError:
            continue
    return env


_ENV = _load_env()


def _env(key, default=None):
    """Διαβάζει από .env, αλλιώς από OS env, αλλιώς default."""
    return os.environ.get(key) or _ENV.get(key) or default


def _version_newer(a, b):
    """Συγκρίνει δύο σημασιολογικές εκδόσεις (π.χ. '1.2.0' > '1.1.9'). True αν a > b."""
    try:
        pa = [int(x) for x in str(a).split(".")[:3]]
        pb = [int(x) for x in str(b).split(".")[:3]]
        while len(pa) < 3: pa.append(0)
        while len(pb) < 3: pb.append(0)
        return pa > pb
    except Exception:
        return str(a) != str(b) and bool(a)


def _log_error(msg):
    """Γράφει ένα σφάλμα στο error.log (στον φάκελο δεδομένων), με timestamp.

    File logging — ώστε να ξέρουμε τι έσκασε και πότε, ακόμα κι αν το app
    κλείσει μετά. Ποτέ δεν πετάει exception (το logging δεν πρέπει να σπάει τίποτα).
    """
    try:
        log_path = os.path.join(db.data_dir(), "error.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {msg}\n")
    except Exception:
        pass


def _web_dir():
    """Βρίσκει τον φάκελο web/, είτε τρέχει κανονικά είτε μέσα από PyInstaller."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "web")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")


def _web_override_dir():
    """Μόνιμος φάκελος για frontend updates — ζει στο data_dir (επιζεί από reinstall).
    Αν υπάρχει νεότερο index.html εκεί, κερδίζει το built-in."""
    return os.path.join(db.data_dir(), "web")


def _index_html_path():
    """Επιστρέφει το ΣΩΣΤΟ index.html: το override (αν υπάρχει) αλλιώς το built-in."""
    override = os.path.join(_web_override_dir(), "index.html")
    if os.path.exists(override):
        return override
    return os.path.join(_web_dir(), "index.html")


def _fetch_bytes(url, timeout=8, ua="Mozilla/5.0 (privacy-yt)"):
    """Κατεβάζει bytes από ένα URL (με user-agent). Επιστρέφει bytes ή None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def _fetch_text(url, timeout=8, ua="Mozilla/5.0 (privacy-yt)"):
    """Κατεβάζει κείμενο (utf-8) από ένα URL. Επιστρέφει str ή None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        return None


def _safe_key(key):
    """🔒 Καθαρίζει ένα video/channel id ώστε να είναι ΑΣΦΑΛΕΣ ως filename.
    Τα YouTube ids περιέχουν μόνο [A-Za-z0-9_-]. Οτιδήποτε άλλο (/.\\ κλπ)
    απορρίπτεται — αποτρέπει path traversal / arbitrary file read/write."""
    s = str(key or "").strip()
    if not s or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", s):
        return None
    return s


def _cached_file(subdir, key, ext=".jpg"):
    """Επιστρέφει το path ενός cached αρχείου (χωρίς να το κατεβάσει).
    🔒 Το key sanitize-άρεται (whitelist chars) — κανένα path traversal."""
    safe = _safe_key(key)
    if safe is None:
        return None
    d = os.path.join(db.data_dir(), subdir)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{safe}{ext}")
    # 🔒 Διπλή άμυνα: επιβεβαίωσε ότι το τελικό path μένει ΜΕΣΑ στο subdir.
    if not os.path.realpath(path).startswith(os.path.realpath(d) + os.sep):
        return None
    return path


def get_thumbnail(video_id):
    """Κατεβάζει (μία φορά) και σερβίρει το thumbnail τοπικά — η Google δεν το μαθαίνει."""
    if not video_id:
        return None
    path = _cached_file("thumbs", video_id)
    if os.path.exists(path):
        return path
    data = _fetch_bytes(f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg")
    if data is None:
        return None
    with open(path, "wb") as f:
        f.write(data)
    return path


# 🚀 Prefetch pool: κατεβάζει thumbnails ΠΑΡΑΛΛΗΛΑ (8 μαζί) στο background,
#    ώστε το πρώτο φόρτωμα σε νέο PC να μη «περιμένει» ένα-ένα (ήταν το bottleneck).
_PREFETCH_POOL = ThreadPoolExecutor(max_workers=8)
_PREFETCH_INFLIGHT = set()
_PREFETCH_LOCK = threading.Lock()


def prefetch_thumbnails(video_ids, include_small=True):
    """Κατεβάζει παράλληλα τα thumbnails (big + small) στο background.
    Αγνοεί ό,τι είναι ήδη cached. Ασφαλές να κληθεί πολλές φορές (dedupe)."""
    if not video_ids:
        return
    todo = []
    for vid in video_ids:
        if not vid:
            continue
        big = _cached_file("thumbs", vid)
        if not os.path.exists(big):
            todo.append(("thumbs", vid, f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"))
        if include_small:
            small = _cached_file("thumbs_small", vid)
            if not os.path.exists(small):
                todo.append(("thumbs_small", vid, f"https://i.ytimg.com/vi/{vid}/default.jpg"))
    if not todo:
        return

    def _one(job):
        folder, vid, url = job
        with _PREFETCH_LOCK:
            if vid in _PREFETCH_INFLIGHT:
                return
            _PREFETCH_INFLIGHT.add(vid)
        try:
            path = _cached_file(folder, vid)
            if os.path.exists(path):
                return
            data = _fetch_bytes(url, timeout=6)
            if data:
                with open(path, "wb") as f:
                    f.write(data)
        except Exception:
            pass
        finally:
            with _PREFETCH_LOCK:
                _PREFETCH_INFLIGHT.discard(vid)

    try:
        for job in todo:
            _PREFETCH_POOL.submit(_one, job)
    except Exception:
        pass


def get_thumbnail_small(video_id):
    """Μικρό thumbnail (120x90) για blur-up placeholder — φορτώνει σχεδόν αμέσως."""
    if not video_id:
        return None
    path = _cached_file("thumbs_small", video_id)
    if os.path.exists(path):
        return path
    data = _fetch_bytes(f"https://i.ytimg.com/vi/{video_id}/default.jpg")
    if data is None:
        return None
    with open(path, "wb") as f:
        f.write(data)
    return path


def get_dominant_color(video_id):
    """Υπολογίζει (μία φορά) το επικρατές χρώμα του thumbnail — cache σε .color.
    Χρησιμοποιεί το μικρό default.jpg (γρήγορο download) — αρκετό για το placeholder χρώμα."""
    if not video_id:
        return None
    color_path = _cached_file("thumbs", video_id, ext=".color")
    if os.path.exists(color_path):
        try:
            with open(color_path, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    small = get_thumbnail_small(video_id)
    if not small:
        return None
    try:
        from PIL import Image
        img = Image.open(small).convert("RGB").resize((16, 16))
        px = list(img.getdata())
        n = len(px)
        color = "#%02x%02x%02x" % (
            sum(p[0] for p in px) // n,
            sum(p[1] for p in px) // n,
            sum(p[2] for p in px) // n,
        )
    except Exception:
        return None
    try:
        with open(color_path, "w") as f:
            f.write(color)
    except Exception:
        pass
    return color


def _resolve_channel_name(channel_id):
    """🔒 Επιστρέφει το όνομα ενός καναλιού από το channel_id.
    Πρώτα από το channel_watch (cache), αλλιώς scraping του channel page.
    Επιστρέφει None αν δεν βρεθεί — ο caller χρησιμοποιεί το channel_id ως fallback."""
    if not channel_id:
        return None
    # 1) cache από channel_watch (όνομα αν υπάρχει)
    try:
        meta = db.channel_watch_meta()
        nm = (meta.get(channel_id) or {}).get("name") if isinstance(meta.get(channel_id), dict) else None
        if nm and nm.strip():
            return nm.strip()
    except Exception:
        pass
    # 2) scraping του channel page
    try:
        html = _fetch_text(f"https://www.youtube.com/channel/{channel_id}", timeout=8)
        if html:
            m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return None


def get_channel_avatar(channel_id):
    """Κατεβάζει (μία φορά) το avatar του καναλιού, τοπικά — scraping του channel page."""
    if not channel_id:
        return None
    path = _cached_file("avatars", channel_id)
    if os.path.exists(path):
        return path
    html = _fetch_text(f"https://www.youtube.com/channel/{channel_id}")
    if html is None:
        return None
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if not m:
        return None
    data = _fetch_bytes(m.group(1))
    if data is None:
        return None
    with open(path, "wb") as f:
        f.write(data)
    return path


def scrape_video_info(video_id):
    """Scrape το video page για channel_id + channel + title (για lazy backfill)."""
    html = _fetch_text(
        "https://www.youtube.com/watch?v=" + video_id,
        timeout=12,
        ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )
    if html is None:
        return None
    info = {}
    m = re.search(r'"channelId":"(UC[^"]+)"', html)
    if m:
        info["channel_id"] = m.group(1)
    m = re.search(r'"author":"([^"]+)"', html)
    if m:
        info["channel"] = m.group(1)
    m = re.search(r'<meta name="title" content="([^"]+)"', html)
    if m:
        info["title"] = m.group(1)
    return info or None


def check_embeddable(video_id):
    """Ελέγχει το YouTube oEmbed endpoint αν ένα βίντεο επιτρέπει ενσωμάτωση (embed).

    Επιστρέφει:
        True  → 200 OK (embed επιτρέπεται)
        False → 401/403 (ο owner απενεργοποίησε το embed / private / deleted)
        None  → timeout/network/άλλο (άγνωστο — αφήνουμε το frontend να δοκιμάσει iframe)
    """
    url = (
        "https://www.youtube.com/oembed?url="
        + urllib.parse.quote("https://www.youtube.com/watch?v=" + video_id)
        + "&format=json"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False
        return None
    except Exception:
        return None


def _probe_embeddable(video_id, timeout=2.5):
    """Ρωτά το YouTube oEmbed. Επιστρέφει (ok, definitive).
    definitive=True μόνο για σαφή απάντηση (200 → παίζει, 401/403 → μπλοκαρισμένο).
    Timeout/δίκτυο/άλλο σφάλμα → (True, False): fail-open ΧΩΡΙΣ να αποθηκευτεί."""
    try:
        url = (
            "https://www.youtube.com/oembed?url="
            + urllib.parse.quote("https://www.youtube.com/watch?v=" + video_id)
            + "&format=json"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (resp.status == 200), (resp.status == 200)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, True
        return True, False
    except Exception:
        return True, False


def filter_embeddable(video_ids):
    """Από μια λίστα video_id, κρατάει ΜΟΝΟ όσα επιτρέπουν embed.

    ⚡ ΕΝΑ query για όλη τη cache → έλεγχος δικτύου ΜΟΝΟ για τα άγνωστα (παράλληλα) →
       ΜΙΑ εγγραφή για τα νέα. Η 2η αναζήτηση της ίδιας λέξης δεν κάνει καθόλου δίκτυο."""
    if not video_ids:
        return []
    known = db.get_embeddable_many(video_ids)
    unknown = [v for v in dict.fromkeys(video_ids) if v not in known]
    verdict = dict(known)
    if unknown:
        with ThreadPoolExecutor(max_workers=12) as ex:
            probed = list(ex.map(_probe_embeddable, unknown))
        to_save = {}
        for vid, (ok, definitive) in zip(unknown, probed):
            verdict[vid] = ok
            if definitive:
                to_save[vid] = ok
        try:
            db.set_embeddable_many(to_save)
        except Exception:
            pass
    return [vid for vid in video_ids if verdict.get(vid, True)]


def extract_video_id(url):
    """Εξάγει το video_id από ένα YouTube URL (διάφορα format)."""
    url = (url or "").strip()
    if not url:
        return None
    # Απλό 11-χαρακτήρες video_id
    m = re.match(r"^([A-Za-z0-9_-]{11})$", url)
    if m:
        return m.group(1)
    for pat in (
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"/shorts/([A-Za-z0-9_-]{11})",
        r"/embed/([A-Za-z0-9_-]{11})",
        r"[?&]v=([A-Za-z0-9_-]{11})",
    ):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _backfill_one(video_id):
    """Ασύγχρονο backfill: ανακτά channel + channel_id + title για ένα βίντεο."""
    try:
        info = scrape_video_info(video_id)
        if info:
            db.update_video_meta(
                video_id,
                channel_id=info.get("channel_id"),
                channel=info.get("channel"),
                title=info.get("title"),
            )
    except Exception:
        pass


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        # 🔒 Αυστηρό CORS: μόνο localhost (127.0.0.1). Αποτρέπει κακόβουλες ιστοσελίδες (CSRF)
        # από το να κάνουν requests στον τοπικό σου server από τον browser.
        origin = self.headers.get("Origin", "")
        if origin and (origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost")):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")

    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, status, body):
        body = body.encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _video_payload(v):
        """Σειριοποιεί ΕΝΑ βίντεο σε dict για το JSON response (dashboard/search)."""
        return {
            "video_id": v["video_id"],
            "title": v["title"],
            "channel": v["channel"],
            "channel_id": v["channel_id"],
            "category": v["user_category"] or v["category"],
            "watch_count": v["watch_count"],
            "last_watched_at": v["last_watched_at"],
            "rank": v["rank"],
            "pinned": v["pinned"],
            "unseen": v.get("unseen") or 0,
            "rating": v.get("rating") or 0,
            "my_tags": (lambda s: json.loads(s) if s else [])(v.get("my_tags")),
            "pin_top": v.get("pin_top") or 0,
            "cat_rank": v.get("cat_rank") or 0,
        }

    def _dashboard(self):
        vids = db.all_videos()
        stats = db.stats()
        ui = db.get_ui_state()
        # 🔧 Επιστρέφουμε ΟΛΑ τα βίντεο (όχι top 200) — τα «νέα/unseen» πρέπει να φαίνονται όλα
        # στο grid. (Το παλιό vids[:200] έκοβε τα unseen που πέφτανε κάτω από rank>0 βίντεα.)
        recent = [self._video_payload(v) for v in vids]
        # 🚀 Prefetch (background, παράλληλα) των thumbnails των ΠΡΩΤΩΝ βίντεο —
        #    ώστε το πρώτο φόρτωμα σε νέο PC να μη «περιμένει» ένα-ένα.
        try:
            prefetch_thumbnails([v.get("video_id") for v in vids[:60]])
        except Exception:
            pass
        self._json(200, {
            "stats": stats,
            "videos": recent,
            "all_tags": db.all_tags(),
            "channel_tags": db.channel_tags_map(),
            "all_categories": db.all_categories(),
            "channel_watch": db.all_channel_watch(),
            "channel_watch_meta": db.channel_watch_meta(),
            "video_notes": db.all_video_notes(),     # ⚡ μέσα στο ίδιο request (πριν: 2ο request + 2ο render)
            "collapsed": ui.get("collapsed", []),
            "expanded": ui.get("expanded", []),   # ✅ ΝΕΟ: ποια κανάλια άνοιξε ο χρήστης
            "order": ui.get("order", []),
            "tab_order": ui.get("tab_order", []),
            "cat_order": ui.get("cat_order", []),
            "cat_collapsed": ui.get("cat_collapsed", []),
            "cat_pinned": ui.get("cat_pinned", []),
            "rss_shown": ui.get("rss_shown", 6),
            "theme": ui.get("theme", "light"),
            "lang": ui.get("lang", "en"),
            "fox": ui.get("fox", "on"),
            "version": VERSION,
        })

    def _suggest(self, query):
        q = (query or "").strip()
        if not q:
            self._json(200, {"term": q, "suggestions": []})
            return
        try:
            suggs = recommender.fetch_suggestions(q)
        except Exception:
            suggs = []
        self._json(200, {"term": q, "suggestions": suggs})

    def _search(self, query):
        q = (query or "").strip().lower()
        if not q:
            self._json(200, {"query": q, "results": []})
            return
        vids = db.all_videos()
        channel_tags = db.channel_tags_map()
        results = []
        for v in vids:
            key = v.get("channel_id") or v.get("channel") or ""
            try:
                vt = set(json.loads(v.get("my_tags") or "[]"))
            except Exception:
                vt = set()
            vt |= set(channel_tags.get(key, []))
            title = (v.get("title") or "").lower()
            channel = (v.get("channel") or "").lower()
            cat = (v.get("user_category") or v.get("category") or "").lower()
            tags_str = " ".join(t.lower() for t in vt)
            # 📅 Ημερομηνία σε διάφορα formats (έτος, "ηη/μμ/εεεε", "μμ/εεεε") για αναζήτηση.
            date_str = ""
            raw_date = v.get("last_watched_at") or v.get("first_seen_at") or ""
            if raw_date:
                import datetime as _dt
                try:
                    d = _dt.datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
                    date_str = (
                        f"{d.strftime('%d/%m/%Y')} {d.strftime('%m/%Y')} "
                        f"{d.strftime('%Y')} {d.strftime('%d-%m-%Y')} {d.strftime('%B').lower()} {d.strftime('%A').lower()}"
                    )
                except Exception:
                    date_str = str(raw_date).lower()
            # 🔢 watch_count ως κείμενο (για «x3», «3», κλπ)
            count_str = f"x{v.get('watch_count') or 1} {v.get('watch_count') or 1} φορές"
            hay = f"{title} {channel} {cat} {tags_str} {date_str} {count_str}"
            if q in hay:
                results.append(self._video_payload(v))
        # κατάταξη: pinned πρώτα, μετά rating, μετά προβολές
        results.sort(key=lambda x: (not x["pinned"], -(x["rating"] or 0), -(x["watch_count"] or 0)))
        self._json(200, {"query": query or "", "results": results[:100]})

    def _check_new(self):
        """RSS watchdog: για τα παρακολουθούμενα κανάλια τραβά το δημόσιο RSS feed,
        και επιστρέφει τα βίντεο που ΔΕΝ έχεις δει ΚΑΙ ΔΕΝ έχεις απορρίψει (το «σου ξέφυγε»)."""
        watched = db.watch_channels()
        if not watched:
            self._json(200, {"new": [], "message": "Δεν παρακολουθείς κανένα κανάλι ακόμα."})
            return
        seen = set(db.all_video_ids())          # ό,τι έχεις στο ιστορικό σου
        dismissed = set(db.dismissed_ids())      # ό,τι έχεις απορρίψει (×)
        new_items = []
        errors = []
        for cid in watched:
            entries = fetch_rss_with_fallback(cid)
            if entries is None:
                errors.append(cid)
                continue
            for e in entries:
                vid = e.get("video_id")
                if vid and vid not in seen and vid not in dismissed:
                    new_items.append({
                        "video_id": vid,
                        "title": e.get("title", ""),
                        "channel_id": cid,
                        "channel": e.get("channel", ""),
                        "published": e.get("published", ""),
                    })
        # νεότερα πρώτα
        new_items.sort(key=lambda x: x.get("published", ""), reverse=True)
        # 🧹 Φιλτράρισε τα βίντεο που δεν παίζουν (non-embeddable) — δεν τα δείχνουμε ως πρόταση.
        ids = [n["video_id"] for n in new_items]
        ok_ids = set(filter_embeddable(ids))
        new_items = [n for n in new_items if n["video_id"] in ok_ids]
        self._json(200, {"new": new_items, "errors": errors})

    def _send_image(self, path, max_age):
        """Σερβίρει cached εικόνα με Cache-Control, ώστε το WebView να ΜΗΝ τη ζητά ξανά σε κάθε re-render."""
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", f"public, max-age={max_age}")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_thumb(self, video_id):
        path = get_thumbnail(video_id)
        if not path:
            self._json(404, {"error": "no thumbnail"})
            return
        self._send_image(path, 604800)      # thumbnail βίντεο: αμετάβλητο → 7 μέρες

    def _serve_thumb_small(self, video_id):
        path = get_thumbnail_small(video_id)
        if not path:
            self._json(404, {"error": "no thumbnail"})
            return
        self._send_image(path, 604800)

    def _serve_avatar(self, channel_id):
        path = get_channel_avatar(channel_id)
        if not path:
            self._json(404, {"error": "no avatar"})
            return
        self._send_image(path, 86400)       # avatar: μπορεί να αλλάξει σπάνια → 1 μέρα

    def _serve_static(self, rel_path, content_type):
        """Σερβίρει ένα στατικό αρχείο από το web/ folder (fonts/css, κλπ).

        Με Cache-Control: no-cache ώστε τα assets να ξαναδιαβάζονται μετά από build
        (ο WebView2 αλλιώς κρατά cache την παλιά έκδοση).
        """
        full = os.path.join(_web_dir(), rel_path)
        # ασφάλεια: μην αφήνουμε path traversal
        if not os.path.realpath(full).startswith(os.path.realpath(_web_dir())):
            self._json(404, {"error": "not found"})
            return
        # 🌐 FRONTEND OVERRIDE: αν υπάρχει το ίδιο αρχείο στο override dir,
        #    κερδίζει το built-in (ώστε το frontend update να μπορεί να στέλνει
        #    και νέα i18n.json / assets, όχι μόνο index.html).
        try:
            ov_full = os.path.join(_web_override_dir(), rel_path)
            ov_root = os.path.realpath(_web_override_dir())
            if os.path.realpath(ov_full).startswith(ov_root) and os.path.isfile(ov_full):
                full = ov_full
        except Exception:
            pass
        if not os.path.isfile(full):
            self._json(404, {"error": "not found"})
            return
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        try:
            self._handle_get()
        except Exception as e:
            _log_error(f"GET {self.path} → {e}\n{traceback.format_exc()}")
            try:
                self._json(500, {"error": str(e)})
            except Exception:
                pass

    def _handle_get(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            with open(_index_html_path(), encoding="utf-8") as f:
                self._html(200, f.read())
        # 🌐 STATIC: i18n.js / i18n.json / ό,τι άλλο κάθεται στο web/ (όχι index.html)
        elif path.endswith((".js", ".json", ".css", ".svg", ".png", ".woff2")):
            name = path.lstrip("/")
            ctype = {
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".woff2": "font/woff2",
            }.get(os.path.splitext(name)[1], "application/octet-stream")
            self._serve_static(name, ctype)
        elif path == "/api/dashboard":
            self._dashboard()
        elif path == "/api/suggest":
            q = parse_qs(parsed.query).get("q", [""])[0]
            self._suggest(q)
        elif path == "/api/search":
            q = parse_qs(parsed.query).get("q", [""])[0]
            self._search(q)
        elif path.startswith("/thumb/"):
            self._serve_thumb(path.split("/thumb/", 1)[1])
        elif path.startswith("/thumb_small/"):
            self._serve_thumb_small(path.split("/thumb_small/", 1)[1])
        elif path.startswith("/avatar/"):
            self._serve_avatar(path.split("/avatar/", 1)[1])
        elif path == "/health":
            self._json(200, {"ok": True, "videos": db.count_videos()})
        elif path == "/version":
            self._json(200, {"version": VERSION})
        elif path == "/update_check":
            # 🔄 Ελέγχει το latest.json (GitHub) για νεότερη έκδοση. Δεν κατεβάζει τίποτα.
            try:
                req = urllib.request.Request(UPDATE_URL, headers={"User-Agent": "PrivacyYouTuber/1.0"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = json.loads(r.read().decode("utf-8"))
                remote = data.get("version", "")
                newer = _version_newer(remote, VERSION)
                self._json(200, {
                    "ok": True,
                    "current": VERSION,
                    "latest": remote,
                    "newer": newer,
                    "url": data.get("url", ""),
                    "notes": data.get("notes", ""),
                    "frontend_url": data.get("frontend_url", ""),
                    "download_url": data.get("download_url", ""),
                    "update_kind": data.get("update_kind", "full"),
                })
            except Exception as e:
                self._json(200, {"ok": False, "error": str(e), "current": VERSION})
        elif path == "/api/recent-searches":
            self._json(200, {"searches": db.get_recent_searches()})
        elif path == "/api/video-notes":
            vid = parse_qs(parsed.query).get("video_id", [""])[0]
            self._json(200, {"notes": db.get_video_notes(vid)})
        elif path.startswith("/fonts/"):
            self._serve_static(path.lstrip("/"), "font/woff2")
        elif path.endswith(".css"):
            self._serve_static(path.lstrip("/"), "text/css")
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8", "ignore"))
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return
        self._body = data
        try:
            self._handle_post(path, data)
        except Exception as e:
            # Ζώνη ασφαλείας: ό,τι κι αν σκάσει, επιστρέφει καθαρό 500 — ο browser δεν κρεμάει.
            _log_error(f"POST {path} → {e}\n{traceback.format_exc()}")
            try:
                self._json(500, {"error": str(e)})
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────
    # 🔑 LICENSING — βοηθητικά (license.json + Gumroad verify)
    # ─────────────────────────────────────────────────────────────
    def _license_check_off(self):
        """🧪 DEV MODE: αν το .env έχει LICENSE_CHECK=off, το licensing ΠΑΡΑΚΑΜΠΤΕΤΑΙ.
        Χρησιμοποιείται ΜΟΝΟ στο dev μηχάνημα (Desktop build) για εύκολες δοκιμές.
        Το .env ΔΕΝ μπαίνει στο installer build → ο πελάτης έχει ΠΑΝΤΑ check ενεργό."""
        return (_env("LICENSE_CHECK", "").strip().lower() == "off")

    def _license_path(self):
        """⚠️ DEPRECATED — το license state πάει ΠΛΕΟΝ ΣΤΗ ΒΑΣΗ (όχι αρχείο).
        Κράτησε τη μέθοδο για backward-compat αλλά ΔΕΝ χρησιμοποιείται."""
        return os.path.join(db.data_dir(), "license.json")

    def _read_license(self):
        # 🔑 Το license state ζει ΣΤΗ ΒΑΣΗ (ui_state key='license'),
        #    ΟΧΙ σε αρχείο — ώστε να επιζεί από update/uninstall/reinstall.
        return db.get_key("license") or {}

    def _write_license(self, state):
        db.set_key("license", state)

    def _verify_license_once(self, product_id, key, increment_uses):
        """Ένα μόνο call στο Gumroad. Επιστρέφει (http_ok, dict)."""
        try:
            body = urllib.parse.urlencode({
                "product_id": product_id,
                "license_key": key,
                "increment_uses_count": "true" if increment_uses else "false",
            }).encode("utf-8")
            req = urllib.request.Request(
                GUMROAD_VERIFY_URL, data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded",
                         "User-Agent": "PrivacyYouTuber/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                return True, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # 404 = «δεν υπάρχει τέτοιο license» -> μπορούμε να δοκιμάσουμε άλλο format
            try:
                return False, json.loads(e.read().decode("utf-8"))
            except Exception:
                return False, {"success": False, "error": f"HTTP {e.code}"}
        except Exception as e:
            # Δίκτυο/άλλο: ΔΕΝ έχει νόημα retry με άλλο format
            return False, {"success": False, "error": str(e), "_network": True}

    def _verify_license(self, key, increment_uses):
        """Καλεί το Gumroad /v2/licenses/verify — ΧΩΡΙΣ αυτόματες μετατροπές.

        Στέλνει το key ΑΚΡΙΒΩΣ όπως το έδωσε ο χρήστης (μόνο strip κενών).
        Αν το format φαίνεται λάθος (πεζά γράμματα), ΔΕΝ το διορθώνουμε σιωπηλά —
        επιστρέφουμε ειδικό σήμα ώστε το UI να πει στον χρήστη «πρόσεξε τα
        πεζοκεφαλαία». Έτσι ο χρήστης ξέρει τι να κάνει και δεν υπάρχει
        κρυφή συμπεριφορά. Επιστρέφει dict, ΠΟΤΕ δεν ρίχνει.
        """
        # 🔑 .env (dev) → αλλιώς hardcoded default → αλλιώς κενό.
        product_id = _env("GUMROAD_PRODUCT_ID", "") or GUMROAD_PRODUCT_ID_DEFAULT
        raw = (key or "").strip()
        if not raw:
            return {"success": False, "error": "empty key"}

        ok, res = self._verify_license_once(product_id, raw, increment_uses)
        if res.get("success"):
            return res

        # Αν έφταιξε το format (υπάρχουν πεζά), δώσε σαφές, μεταφράσιμο σήμα.
        has_lower = any(ch.islower() for ch in raw)
        if has_lower:
            res = dict(res or {})
            res["error_code"] = "lowercase_key"
        return res

    def _handle_post(self, path, data):
        if path == "/watch":
            db.record_watch(data)
            # Lazy backfill: αν λείπει το channel_id, ανακτήσου το ασύγχρονα (δεν καθυστερεί το response).
            if not data.get("channel_id") and data.get("video_id"):
                threading.Thread(target=_backfill_one, args=(data["video_id"],), daemon=True).start()
            self._json(200, {"ok": True})
        elif path == "/delete":
            db.delete_video(data.get("video_id"))
            self._json(200, {"ok": True})
        elif path == "/delete_channel":
            db.delete_channel(data.get("channel_id"))
            self._json(200, {"ok": True})
        elif path == "/set_category":
            db.set_category(data.get("video_id"), data.get("category"))
            self._json(200, {"ok": True})
        elif path == "/create_category":
            db.create_category(data.get("name"))
            self._json(200, {"ok": True})
        elif path == "/rename_category":
            db.rename_category(data.get("old_name"), data.get("new_name"))
            self._json(200, {"ok": True})
        elif path == "/delete_category":
            db.delete_category(data.get("name"))
            self._json(200, {"ok": True})
        elif path == "/set_video_tags":
            db.set_video_tags(data.get("video_id"), data.get("tags") or [])
            self._json(200, {"ok": True})
        elif path == "/set_video_rating":
            db.set_video_rating(data.get("video_id"), data.get("rating") or 0)
            self._json(200, {"ok": True})
        elif path == "/set_channel_tags":
            db.set_channel_tags(data.get("channel_id"), data.get("tags") or [])
            self._json(200, {"ok": True})
        elif path == "/delete_tag":
            db.delete_tag(data.get("tag"))
            self._json(200, {"ok": True})
        elif path == "/ui_state":
            # 🔁 MERGE: ξεκίνα από το υπάρχον state, ώστε partial updates (π.χ. μόνο theme)
            #    να ΜΗΝ σβήνουν τα υπόλοιπα (tab_order, cat_order, collapsed κ.λπ.).
            try:
                st = dict(db.get_ui_state() or {})
            except Exception:
                st = {}
            for k in ("collapsed", "expanded", "order", "tab_order", "cat_order", "cat_collapsed", "cat_pinned"):
                if k in data and data[k]:
                    st[k] = data[k]
                elif k not in st:
                    st[k] = []
            # Συμβατότητα με την παλιά λογική (αν λείπουν τελείως):
            st.setdefault("collapsed", [])
            st.setdefault("expanded", [])
            st.setdefault("order", [])
            st.setdefault("tab_order", [])
            st.setdefault("cat_order", [])
            st.setdefault("cat_collapsed", [])
            st.setdefault("cat_pinned", [])
            if "rss_shown" in data and isinstance(data["rss_shown"], int) and data["rss_shown"] >= 1:
                st["rss_shown"] = data["rss_shown"]
            # 🌙/☀️ Θέμα (dark/light) — επιμένει στη βάση (το localStorage δεν κρατά στο WebView).
            if data.get("theme") in ("dark", "light"):
                st["theme"] = data["theme"]
            # 🌐 Γλώσσα (en/el) — ίδιος λόγος: το localStorage δεν κρατά στο WebView.
            if data.get("lang") in ("en", "el"):
                st["lang"] = data["lang"]
            # 🦊 Αλεπού αναμονής (on/off) — επιμένει στη βάση (το localStorage δεν κρατά στο WebView).
            if data.get("fox") in ("on", "off"):
                st["fox"] = data["fox"]
            db.set_ui_state(st)
            self._json(200, {"ok": True})
        elif path == "/pin":
            # Νέο: δέχεται προαιρετικό "state" (0/1/2). Αν λείπει → legacy toggle.
            raw_state = data.get("state")
            if raw_state is None:
                pinned = db.toggle_pin(data.get("video_id"))
                self._json(200, {"ok": True, "pinned": pinned})
            else:
                state = int(raw_state)
                new_state = db.set_pin(data.get("video_id"), state)
                self._json(200, {"ok": True, "state": new_state})
        elif path == "/pin_channel":
            new_state = db.toggle_pin_channel(data.get("channel_id"))
            self._json(200, {"ok": True, "pinned": new_state})
        elif path == "/reorder":
            db.reorder_videos(data.get("ordered_ids") or [])
            self._json(200, {"ok": True})
        elif path == "/reorder_cat":
            db.reorder_cat_videos(data.get("ordered_ids") or [])
            self._json(200, {"ok": True})
        elif path == "/watch_channel":
            db.set_channel_watch(data.get("channel_id"), data.get("enabled", True))
            self._json(200, {"ok": True})
        elif path == "/check_new":
            self._check_new()
        elif path == "/search":
            q = (data.get("q") or "").strip()
            if not q:
                self._json(400, {"ok": False, "error": "Δώσε κάτι να ψάξω."})
                return
            # 📄 ΜΙΑ σελίδα = 24 βίντεο (όσο κατεβάζει το YouTube ανά κλήση). Ίδιο νούμερο για ΚΑΤΕΒΑΣΜΑ και ΕΜΦΑΝΙΣΗ:
            #    καμία σπατάλη (πριν: κατέβαζε 24, έδειχνε 10 → 14 πετιόνταν).
            #    Μετρημένο: ytsearch16 ≈ 1,5s — το πιο γρήγορο από τα δοκιμασμένα.
            limit = int(data.get("limit", 24) or 24)
            page_size = max(1, min(48, limit))     # πόσα δείχνει το frontend ανά σελίδα
            mode = (data.get("mode") or "videos").strip()
            offset = int(data.get("offset", 0) or 0)
            # 🔍 ΑΝΑΖΗΤΗΣΗ ΜΕ CACHE (ό,τι κάναμε στα κανάλια):
            #   • ΙΔΙΟ query+mode και ξέρουμε ήδη αποτελέσματα; → ΑΚΑΡΙΑΙΑ από τη βάση.
            #   • Αν λείπει κι άλλο (φτάσαμε στο τέλος της cache) → φέρνουμε φρέσκα & αποθηκεύουμε.
            #   Η CACHE είναι το «σύνολο», όπως το channel_videos_cache — τα «Επόμενα» μηδέν δίκτυο.

            def _chan(rows):
                # Μετατροπή γραμμών cache -> κανάλια (το frontend θέλει channel_id/channel/name).
                out = []
                for r in rows:
                    cid = r.get("channel_id") or r.get("video_id") or ""
                    nomi = r.get("title") or r.get("channel") or ""
                    out.append({"channel_id": cid, "channel": nomi, "name": nomi, "title": nomi})
                return out

            def _from_cache(off, lim):
                rows = db.get_search_results(q, mode, offset=off, limit=lim)
                # Μετατροπή στη μορφή που περιμένει το frontend.
                # ⚠️ ΤΟ «thumb» ΕΙΝΑΙ ΑΠΑΡΑΙΤΗΤΟ: χωρίς αυτό η <img> δεν φορτώνει και μένει το χρώμα.
                out = []
                for r in rows:
                    vid = r.get("video_id") or ""
                    out.append({"video_id": vid, "title": r.get("title") or "",
                                "channel": r.get("channel") or "",
                                "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                                "duration": r.get("duration") or 0, "views": r.get("views") or 0})
                return out

            cached_total = db.count_search_results(q, mode)
            # 📥 Ζητάμε ΠΕΡΙΣΣΟΤΕΡΑ από όσα δείχνουμε: το φίλτρο embed κόβει μερικά,
            #    και χωρίς περίσσευμα η σελίδα «γεμίζει» λιγότερο από 24 → φαινόταν «τέλος»
            #    ενώ το YouTube είχε εκατοντάδες (π.χ. «C» → 23/24 → ΤΕΛΟΣ).
            #    Ζητάμε 2× το page_size ώστε μετά το φίλτρο να μείνουν ≥24.
            CHUNK = max(24, page_size * 2)

            # Αν σε ΠΡΟΗΓΟΥΜΕΝΗ προσπάθεια το δίκτυο δεν έδωσε τίποτα, μην ξαναπροσπαθείς (κόβει τα 13s στο βάθος).
            # ✅ Έχουμε ΟΛΗ τη ζητούμενη σελίδα ή ξέρουμε ότι τελείωσε → απάντηση ΧΩΡΙΣ δίκτυο.
            if db.search_exhausted(q, mode) or cached_total >= offset + page_size:
                rows = _from_cache(offset, page_size)
                # ✅ ΣΥΝΤΗΡΗΤΙΚΟ: Όταν ΔΕΝ ξέρουμε σίγουρα ότι τελείωσε, λέμε «έχει κι άλλα».
                #    Καλύτερα ένα «Επόμενα» που δεν βρίσκει τίποτα, παρά να ΚΡΥΨΟΥΜΕ
                #    εκατοντάδες βίντεο λέγοντας ψεύτικο «τέλος» (συνέβη με το query «C»).
                #    Το οριστικό τέλος το ξέρει ΜΟΝΟ το search_exhausted.
                has_more = True
                if mode == "channels":
                    self._json(200, {"ok": True, "videos": [], "channels": _chan(rows), "has_more": has_more,
                                     "cached": cached_total, "from_cache": True})
                else:
                    self._json(200, {"ok": True, "videos": rows, "channels": [], "has_more": has_more,
                                     "cached": cached_total, "from_cache": True})
                return

            # 🛑 Αν ξέρουμε ότι το YouTube ΕΞΑΝΤΛΗΘΗΚΕ (position -1 στη cache), μη ξαναρωτάς.
            if db.search_exhausted(q, mode):
                rows = _from_cache(offset, page_size)
                if mode == "channels":
                    self._json(200, {"ok": True, "videos": [], "channels": _chan(rows), "has_more": False,
                                     "cached": cached_total, "from_cache": True})
                else:
                    self._json(200, {"ok": True, "videos": rows, "channels": [], "has_more": False,
                                     "cached": cached_total, "from_cache": True})
                return

            # 🌐 Χρειάζεται δίκτυο: ΜΙΑ κλήση με το σωστό πλήθος (CHUNK) — όχι βρόχος.
            #    (Ο βρόχος έκανε 5 κλήσεις × yt-dlp = 25s· μία κλήση ίδιου εύρους = ~6s.)
            res = youtube_search(q, mode=mode, offset=offset, limit=CHUNK)
            fresh = res["videos"] if mode != "channels" else res["channels"]
            # 🧹 Φιλτράρισε non-embeddable — ΜΟΝΟ τα βίντεο (τα κανάλια δεν έχουν video_id).
            if fresh and mode != "channels":
                ok_ids = set(filter_embeddable([v["video_id"] for v in fresh]))
                fresh = [v for v in fresh if v["video_id"] in ok_ids]
            # 💾 Αποθήκευσε στη ΣΩΣΤΗ θέση:
            #    • offset=0 → νέα σελίδα 1: καθάρισε τα παλιά (replace_all=True).
            #    • offset>0 → βάλε τα νέα ΜΕΤΑ τα υπάρχοντα (θέση = offset), ΧΩΡΙΣ να σβήσεις τα προηγούμενα.
            try:
                db.save_search_results(q, mode, fresh, start=offset, replace_all=(offset == 0))
                # 🛑 «Εξαντλήθηκε» ΜΟΝΟ αν το YouTube (πριν το φίλτρο) δεν έδωσε απολύτως τίποτα.
                if not (res.get("videos") if mode != "channels" else res.get("channels")):
                    db.mark_search_exhausted(q, mode)
            except Exception:
                pass
            rows = _from_cache(offset, page_size)
            # ✅ «Έχει κι άλλα;» = ΤΟ YOUTUBE έδωσε όσα ζητήσαμε (πριν το φίλτρο) —
            #    ΟΧΙ αν γέμισε η σελίδα μας. Αλλιώς ένα κομμένο βίντεο έλεγε «τέλος».
            kept = db.count_search_results(q, mode)          # πόσα έχουμε συνολικά στη cache
            # ✅ Πήραμε ΑΠΟΤΕΛΕΣΜΑΤΑ από το YouTube → υποθέτουμε ότι έχει κι άλλα.
            #    (Ο server δεν ξέρει το σύνολο του YouTube — ας μη «κλείνει την πόρτα».)
            more_available = bool(res.get("videos") if mode != "channels" else res.get("channels"))
            if mode == "channels":
                self._json(200, {"ok": True, "videos": [], "channels": _chan(rows),
                                 "has_more": more_available,
                                 "cached": kept, "from_cache": False})
            else:
                self._json(200, {"ok": True, "videos": rows, "channels": [],
                                 "has_more": more_available,
                                 "cached": kept, "from_cache": False})
        elif path == "/colors":
            # 🎨 Ασύγχρονο batch dominant color — το frontend το καλεί ΜΕΤΑ το render (δεν μπλοκάρει το search).
            ids = data.get("ids") or []
            ids = [i for i in ids[:48] if i]
            colors = {}

            def _col(vid):
                try:
                    return vid, get_dominant_color(vid)
                except Exception:
                    return vid, None

            if ids:
                with ThreadPoolExecutor(max_workers=8) as ex:     # ⚡ παράλληλα (πριν: σειριακά)
                    for vid, c in ex.map(_col, ids):
                        if c:
                            colors[vid] = c
            self._json(200, {"ok": True, "colors": colors})
        elif path == "/recent_search":
            db.add_recent_search(data.get("q"))
            self._json(200, {"ok": True, "searches": db.get_recent_searches()})
        elif path == "/add_note":
            vid = data.get("video_id")
            if not vid:
                self._json(400, {"ok": False, "error": "Λείπει video_id."})
                return
            nid = db.add_video_note(vid, data.get("title"), data.get("note"), data.get("timestamp_sec", 0))
            self._json(200, {"ok": True, "id": nid, "notes": db.get_video_notes(vid)})
        elif path == "/delete_note":
            db.delete_video_note(data.get("note_id"))
            self._json(200, {"ok": True, "notes": db.get_video_notes(data.get("video_id"))})
        elif path == "/channel_preview":
            cid = (data.get("channel_id") or "").strip()
            if not cid:
                self._json(400, {"ok": False, "error": "Λείπει channel_id."})
                return
            self._json(200, {"ok": True, "preview": channel_preview(cid)})
        elif path == "/channel_videos":
            cid = (data.get("channel_id") or "").strip()
            offset = int(data.get("offset", 0) or 0)
            limit = int(data.get("limit", 10) or 10)
            limit = max(1, min(50, limit))
            if not cid:
                self._json(400, {"ok": False, "error": "Λείπει channel_id."})
                return
            cached_count = db.count_cached_channel_videos(cid)
            # Αν η cache είναι άδεια (πρώτη φορά) → τράβα 50 από yt-dlp και cache-αρέ τα.
            if cached_count == 0:
                fetched = fetch_channel_videos_ytdlp(cid, limit=50) or []
                db.cache_channel_videos(cid, fetched)
            page = db.get_cached_channel_videos(cid, offset=offset, limit=limit)
            total = db.count_cached_channel_videos(cid)
            self._json(200, {"ok": True, "videos": page, "total": total,
                             "has_more": offset + limit < total})
        elif path == "/fetch_channel":
            # 📡 «Επόμενα» σε ένα κανάλι — ΕΞΥΠΝΟ, δύο φάσεις:
            #   ΦΑΣΗ 1 (ψυχρή cache): κατεβάζει ΟΛΟ το ιστορικό (500) μία φορά, το αποθηκεύει
            #                         στη channel_videos_cache, και δίνει τα πρώτα N άγνωστα.
            #   ΦΑΣΗ 2 (ζεστή cache): ΜΗΔΕΝ δίκτυο — δίνει την επόμενη παρτίδα από τη βάση.
            #   Αν το κανάλι αποκτήσει νέα βίντεο, το φθηνό RSS το καταλαβαίνει και ξαναγεμίζει.
            cid = (data.get("channel_id") or "").strip()
            if not cid:
                self._json(400, {"ok": False, "error": "Λείπει channel_id."})
                return
            limit = max(1, min(48, int(data.get("limit", 24) or 24)))
            offset = max(0, int(data.get("offset", 0) or 0))

            cached_n = db.count_cached_channel_videos(cid)
            known_first = db.first_cached_channel_video(cid)

            # 🧠 Χρειάζεται ξαναγέμισμα; (πρώτη φορά, ή το RSS δείχνει νεότερο βίντεο απ' ό,τι ξέρουμε)
            need_refill = cached_n == 0
            if not need_refill and known_first:
                rss_probe = fetch_rss(cid)
                if rss_probe and rss_probe[0].get("video_id") != known_first:
                    need_refill = True

            if need_refill:
                # ΦΑΣΗ 1: ένα βαθύ κατέβασμα (500) → μετά ΟΛΑ είναι τοπικά.
                from concurrent.futures import ThreadPoolExecutor as _TPE
                with _TPE(max_workers=2) as _ex:
                    _f_rss = _ex.submit(fetch_rss, cid)
                    _f_yt = _ex.submit(fetch_channel_videos_ytdlp, cid, 500)
                    try:
                        rss_entries = _f_rss.result() or []
                    except Exception:
                        rss_entries = []
                    try:
                        yt_entries = _f_yt.result() or []
                    except Exception:
                        yt_entries = []
                # Ένωση: RSS (φρέσκα) πρώτα, μετά το yt-dlp — χωρίς διπλά.
                seen_ids = set()
                entries = []
                for e in list(rss_entries) + list(yt_entries):
                    vid = e.get("video_id")
                    if not vid or vid in seen_ids:
                        continue
                    seen_ids.add(vid)
                    entries.append(e)
                if entries:
                    try:
                        db.cache_channel_videos(cid, entries)
                    except Exception:
                        pass

            # ΦΑΣΗ 2: δώσε από τη cache — ΜΗΔΕΝ δίκτυο.
            #   ⚠️ Το offset μετρά ΘΕΣΕΙΣ ΣΤΗ CACHE (όχι «πόσα νέα πήρα»): τα πρώτα πολλά
            #   είναι ήδη γνωστά/πεταμένα, γι' αυτό ένα σκέτο +24 θα ξαναδιάβαζε τις ίδιες θέσεις.
            seen = set(db.all_video_ids())
            dismissed = set(db.dismissed_ids())
            all_cached = db.get_cached_channel_videos(cid, offset=0, limit=5000)
            new_items = []
            cursor = offset
            for e in all_cached[offset:]:
                cursor += 1
                vid = e.get("video_id")
                if not vid or vid in seen or vid in dismissed:
                    continue
                new_items.append({
                    "video_id": vid,
                    "title": e.get("title") or vid,
                    "channel": "",
                    "channel_id": cid,
                    "published": "",
                })
                if len(new_items) >= limit:
                    break
            next_offset = cursor              # ← η ΘΕΣΗ στη cache όπου σταματήσαμε
            has_more = next_offset < len(all_cached)
            self._json(200, {
                "ok": True,
                "videos": new_items,
                "has_more": has_more,
                "next_offset": next_offset,
                "total_cached": len(all_cached),
            })
        elif path == "/add_many":
            # 📡 Μαζική προσθήκη (για fetch) — ΧΩΡΙΣ scrape (τα metadata τα ξέρουμε ήδη).
            # items: [{video_id, title, channel, channel_id}...]. Πολύ πιο γρήγορο από 24 χωριστά /add.
            items = data.get("items") or []
            added = []
            # 🔒 Αν λείπουν ονόματα, κατέβασέ τα ΜΙΑ φορά ανά channel_id (cache στο channel_watch).
            name_cache = {}
            # 🚫 ΠΟΤΕ ξανά ό,τι έχεις διαγράψει: το − / το × είναι οριστικά.
            _dismissed = set(db.dismissed_ids())
            for it in items:
                vid = it.get("video_id")
                if not vid:
                    continue
                if vid in _dismissed:
                    continue                      # το πέταξες → δεν ξαναμπαίνει ΠΟΤΕ
                ch = (it.get("channel") or "").strip()
                cid = (it.get("channel_id") or "").strip()
                if not ch and cid:
                    if cid not in name_cache:
                        name_cache[cid] = _resolve_channel_name(cid)
                    ch = name_cache[cid] or cid
                db.record_watch({
                    "video_id": vid,
                    "title": it.get("title") or vid,
                    "channel": ch,
                    "channel_id": cid,
                    "unseen": bool(it.get("mark_unseen", True)),
                })
                added.append(vid)
            self._json(200, {"ok": True, "added": added})
        elif path == "/dismiss_video":
            db.dismiss_video(data.get("video_id"))
            self._json(200, {"ok": True})
        elif path == "/add":
            vid = extract_video_id(data.get("url", ""))
            if not vid:
                self._json(400, {"ok": False, "error": "Δεν κατάλαβα το link — δώσε ένα YouTube URL."})
                return
            info = scrape_video_info(vid) or {}
            # ✅ Χειροκίνητο ➕ (URL, search) = εγκεκριμένο (unseen=0).
            # 📡 Fetch από feed → unseen=1 (δείχνει NEW badge μέχρι να το δεις).
            mark_unseen = bool(data.get("mark_unseen", False))
            cid = (data.get("channel_id") or "").strip() or info.get("channel_id")
            chname = (data.get("channel") or "").strip() or info.get("channel")
            db.record_watch({
                "video_id": vid,
                "title": info.get("title") or vid,
                "channel": chname,
                "channel_id": cid,
                "unseen": mark_unseen,
            })
            self._json(200, {"ok": True, "video_id": vid, "title": info.get("title") or vid})
        elif path == "/mark_seen":
            db.mark_video_seen(data.get("video_id"))
            self._json(200, {"ok": True})
        elif path == "/mark_unseen_off":
            db.mark_video_unseen_off(data.get("video_id"))
            self._json(200, {"ok": True})
        elif path == "/embeddable":
            vid = data.get("video_id")
            if not vid:
                self._json(400, {"ok": False, "error": "missing video_id"})
                return
            # 1) cache στη βάση (αν το ξέραμε ήδη, επέστρεψε χωρίς νέο HTTP)
            cached = db.get_embeddable(vid)
            if cached is not None:
                self._json(200, {"embeddable": cached})
                return
            # 2) αλλιώς ρώτα το YouTube oEmbed + αποθήκευσε
            result = check_embeddable(vid)
            if result is not None:
                db.set_embeddable(vid, result)
            self._json(200, {"embeddable": result})
        elif path == "/export":
            self._do_export()
        elif path == "/import":
            self._do_import()
        elif path == "/import_subscriptions":
            self._import_subscriptions()
        elif path == "/activate_license":
            # 🧪 DEV MODE: αν LICENSE_CHECK=off, «ενεργοποίησε» αμέσως — χωρίς key.
            if self._license_check_off():
                state = {"activated": True, "license_key": "DEV-BYPASS",
                         "last_check": datetime.now().isoformat(), "fail_count": 0}
                self._write_license(state)
                self._json(200, {"ok": True, "activated": True, "dev": True})
                return
            # 🔑 ΠΡΩΤΗ ενεργοποίηση (online υποχρεωτικά). Ανεβάζει το uses.
            key = (data.get("license_key") or "").strip()
            if not key:
                self._json(400, {"ok": False, "error": "Δώσε το license key."})
                return
            res = self._verify_license(key, increment_uses=True)
            purchase = res.get("purchase") or {}
            if res.get("success") and not purchase.get("refunded") and not purchase.get("disputed") \
                    and int(res.get("uses", 0)) <= LICENSE_MAX_USES:
                state = {
                    "activated": True,
                    "license_key": key,
                    "last_check": datetime.now().isoformat(),
                    "fail_count": 0,
                }
                self._write_license(state)
                self._json(200, {"ok": True, "activated": True})
            elif not res.get("success"):
                # 🌐 Ο server στέλνει ΜΟΝΟ error_code — το frontend μεταφράζει
                #    (en/el). Το «error» μένει ως αγγλικό fallback για κάθε
                #    άγνωστη περίπτωση.
                payload = {"ok": False, "activated": False,
                           "error": "Invalid key or connection problem."}
                # 🔤 Αιτία format: το key είχε πεζά -> πες το ξεκάθαρα στο UI.
                if res.get("error_code") == "lowercase_key":
                    payload["error_code"] = "lowercase_key"
                # 🌐 Αιτία δικτύου: ξεχώρισέ το από «λάθος key».
                elif res.get("_network"):
                    payload["error_code"] = "network"
                self._json(200, payload)
            else:
                # Refund / chargeback / υπερβολικές ενεργοποιήσεις.
                self._json(200, {"ok": False, "activated": False,
                                 "error_code": "revoked",
                                 "error": "This key has been used too many times, or the purchase was refunded."})
        elif path == "/verify_license":
            # 🧪 DEV MODE: αν LICENSE_CHECK=off, πες «ενεργό» αμέσως — χωρίς δίκτυο, χωρίς Gumroad.
            if self._license_check_off():
                self._json(200, {"ok": True, "activated": True, "dev": True})
                return
            # 🔑 Σιωπηλός επανέλεγχος (3 μέρες, ΔΕΝ ανεβάζει uses). Ο τίμιος δεν βλέπει τίποτα.
            state = self._read_license()
            key = state.get("license_key") or (data.get("license_key") or "").strip()
            if not state.get("activated") and not key:
                self._json(200, {"ok": False, "activated": False, "needs_activation": True})
                return
            # Πέρασε το LICENSE_RECHECK_DAYS από το τελευταίο επιτυχημένο check;
            try:
                last = datetime.fromisoformat(state.get("last_check", "")) if state.get("last_check") else None
            except ValueError:
                last = None
            if last and (datetime.now() - last).days < LICENSE_RECHECK_DAYS:
                self._json(200, {"ok": True, "activated": True, "grace": False})
                return
            # Κάνε τον έλεγχο (fail-open: αν ΔΕΝ μπορείς να φτάσεις το Gumroad, δώσε 1 χάρη).
            res = self._verify_license(key, increment_uses=False)
            purchase = res.get("purchase") or {}
            if res.get("success") and not purchase.get("refunded") and not purchase.get("disputed") \
                    and int(res.get("uses", 0)) <= LICENSE_MAX_USES:
                state.update({"activated": True, "last_check": datetime.now().isoformat(), "fail_count": 0})
                self._write_license(state)
                self._json(200, {"ok": True, "activated": True, "grace": False})
            elif purchase.get("refunded") or purchase.get("disputed") or \
                    (res.get("success") and int(res.get("uses", 0)) > LICENSE_MAX_USES):
                # Οριστικό κλείσιμο — refund ή μη νόμιμη χρήση. Καμία χάρη.
                state.update({"activated": False, "fail_count": 99})
                self._write_license(state)
                # 🌐 Στέλνουμε error_code· το frontend το μεταφράζει (en/el).
                self._json(200, {"ok": False, "activated": False,
                                 "error_code": "revoked",
                                 "error": "The license has been cancelled or used excessively."})
            else:
                # 🔌 ΔΕΝ φτάσαμε το Gumroad (offline / API down / 404 / 5xx).
                #    ΑΝ ο χρήστης είχε ποτέ περάσει επιτυχώς τον έλεγχο τοπικά
                #    (activated==True στο state), τον ΑΦΗΝΟΥΜΕ ΠΑΝΤΑ να δουλέψει.
                #    Δεν κλειδώνουμε ΠΟΤΕ τίμιο πελάτη λόγω δικτύου ή Gumroad
                #    downtime. Hard-lock ΜΟΝΟ σε ρητό αρνητικό flag (refund/
                #    disputed/uses>MAX) — αυτό ελέγχεται ΠΑΡΑΠΑΝΩ, με έγκυρο JSON.
                state["fail_count"] = int(state.get("fail_count", 0)) + 1
                self._write_license(state)
                self._json(200, {"ok": True, "activated": True, "grace": True,
                                 "fails_left": -1})
        elif path == "/frontend_update":
            # 🚀 Αυτόματο frontend update: κατεβάζει το νέο index.html και το βάζει
            #    στο ΜΟΝΙΜΟ override φάκελο (data_dir/web/). ΔΕΝ χρειάζεται reinstall.
            #    Ο server προτιμά το override από το built-in (_index_html_path).
            frontend_url = (data.get("frontend_url") or "").strip()
            if not frontend_url:
                self._json(400, {"ok": False, "error": "Λείπει frontend_url."})
                return
            html = _fetch_bytes(frontend_url, timeout=30)
            if not html:
                self._json(200, {"ok": False, "error": "Δεν κατέβηκε το αρχείο."})
                return
            override_dir = _web_override_dir()
            os.makedirs(override_dir, exist_ok=True)
            target = os.path.join(override_dir, "index.html")
            try:
                with open(target, "wb") as f:
                    f.write(html)
            except OSError as e:
                self._json(200, {"ok": False, "error": f"Δεν γράφτηκε: {e}"})
                return
            # 🌐 Κατέβασε ΚΑΙ το i18n.json (νέα keys/μεταφράσεις) από τον ίδιο φάκελο
            #    του frontend_url — αλλιώς το UI θα δείχνει raw keys (π.χ. help.title).
            extra = {}
            try:
                base = frontend_url.rsplit("/", 1)[0]
                for asset in ("i18n.json", "i18n.js"):
                    blob = _fetch_bytes(base + "/" + asset, timeout=20)
                    if blob:
                        with open(os.path.join(override_dir, asset), "wb") as f:
                            f.write(blob)
                        extra[asset] = len(blob)
            except Exception:
                pass
            self._json(200, {"ok": True, "bytes": len(html), "extra": extra,
                             "message": "Ενημέρωση UI ολοκληρώθηκε. Κλείσε ξανά την εφαρμογή."})
        else:
            self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        # Ενεργό logging — βοηθάει στη διάγνωση. Κάθε request τυπώνεται.
        print(f"[{self.command}] {self.path}", flush=True)

    def _do_export(self):
        """Φτιάχνει ένα JSON με ΟΛΑ τα δεδομένα και το αποθηκεύει μέσω native dialog."""
        try:
            data = db.export_all()
            default_name = f"privacy-yt-backup-{datetime.now().strftime('%Y-%m-%d')}.json"
            default_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            path = _ask_save_path(
                title="Εξαγωγή Privacy-YouTuber",
                default_dir=default_dir,
                default_name=default_name,
                filetypes=[("JSON αρχείο", "*.json"), ("Όλα τα αρχεία", "*.*")],
            )
            if not path:  # ο χρήστης ακύρωσε
                self._json(200, {"ok": False, "cancelled": True})
                return
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._json(200, {"ok": True, "path": path})
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})

    def _do_import(self):
        """Φορτώνει ένα JSON export μέσω native dialog και το γράφει στη βάση.

        Mode έρχεται από το request body (το frontend ρωτάει «αντικατάσταση ή συγχώνευση»):
        - replace → σβήνει τα πάντα, βάζει το αρχείο.
        - merge   → προσθέτει χωρίς διπλότυπα.
        """
        try:
            mode = (self._body or {}).get("mode", "replace")
            path = _ask_open_path(
                title="Εισαγωγή Privacy-YouTuber",
                filetypes=[("JSON αρχείο", "*.json"), ("Όλα τα αρχεία", "*.*")],
            )
            if not path:
                self._json(200, {"ok": False, "cancelled": True})
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            db.import_all(data, mode=mode)
            self._json(200, {"ok": True, "path": path, "mode": mode})
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})

    def _import_subscriptions(self):
        """Διαβάζει το subscriptions.csv (Google Takeout) και βάζει τα κανάλια ως «παρακολουθούμενα»."""
        try:
            path = _ask_open_path(
                title="Εισαγωγή καναλιών (subscriptions.csv)",
                filetypes=[("CSV αρχείο", "*.csv"), ("Όλα τα αρχεία", "*.*")],
            )
            if not path:
                self._json(200, {"ok": False, "cancelled": True})
                return
            from . import importer
            subs = importer.parse_subscriptions_csv_with_names(path)
            if not subs:
                self._json(200, {"ok": False, "error": "Δεν βρήκα κανάλια στο αρχείο."})
                return
            for s in subs:
                db.set_channel_watch(s["id"], False, s["name"])
            self._json(200, {"ok": True, "count": len(subs)})
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})


def _open_private(url):
    """Ανοίγει το dashboard σε incognito/private window (Brave → Chrome → Edge → fallback)."""
    import subprocess
    import shutil
    brave_paths = (
        os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    )
    for p in brave_paths:
        if os.path.exists(p):
            subprocess.Popen([p, "--incognito", url], creationflags=_NO_WINDOW)
            return
    chrome = shutil.which("chrome.exe") or shutil.which("chrome") or shutil.which("google-chrome")
    if chrome:
        subprocess.Popen([chrome, "--incognito", url], creationflags=_NO_WINDOW)
        return
    edge = shutil.which("msedge.exe")
    if edge:
        subprocess.Popen([edge, "--inprivate", url], creationflags=_NO_WINDOW)
        return
    webbrowser.open(url)




def _kill_orphan_webviews():
    """Καθαρίζει τα WebView2 processes μετά το κλείσιμο του παραθύρου.

    Γιατί: το pywebview/WebView2 αφήνει ορφανά msedgewebview2 processes (~400MB, 6 procs)
    που συνεχίζουν να τρέχουν και να ζεσταίνουν το μηχάνημα.

    Πώς: το WebView2 root process έχει parent = τη δική μας διεργασία, και όλα τα
    child renderers κρέμονται από αυτό το root. Σκοτώνοντας ΜΟΝΟ το root, τα παιδιά
    πεθαίνουν μαζί (συμπεριφορά Chromium). Δεν αγγίζουμε WebView2 άλλων εφαρμογών.
    """
    import subprocess
    mypid = os.getpid()
    try:
        # Χρησιμοποιούμε PowerShell (το wmic είναι deprecated/απόν από τα Win11).
        ps = (
            "$me=" + str(mypid) + "; "
            "Get-CimInstance Win32_Process -Filter \"Name='msedgewebview2.exe'\" "
            "-ErrorAction SilentlyContinue | "
            "Where-Object { $_.ParentProcessId -eq $me } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, timeout=10,
            creationflags=_NO_WINDOW,      # 🪟 κρύβει το παράθυρο κονσόλας (ήταν ορατό!)
        )
    except Exception:
        pass

def _open_window(url):
    """Ανοίγει το app σε native window (pywebview) αν υπάρχει· αλλιώς στον browser.

    Ο στόχος: ένα «σωστό» παράθυρο εφαρμογής (χωρίς cold-start του browser/incognito),
    που μεταφράζεται εύκολα και σε tablet/κινητό. Το browser μένει σαν fallback.

    Κόλπο για το «λαγκ» στο πρώτο typing: φτιάχνουμε το παράθυρο με `hidden=True`,
    φορτώνουμε τη σελίδα, και το εμφανίζουμε ΜΟΝΟ αφού πυροδοτηθεί το event `loaded`
    — έτσι ο WebView2 engine «ζεσταίνεται» στο παρασκήνιο και το input είναι άμεσα έτοιμο.
    """
    try:
        import webview
        # 📋 Native clipboard για τον πελάτη: το WebView2 ΔΕΝ επιτρέπει
        #    navigator.clipboard ούτε native right-click menu (το pywebview
        #    κλείνει τα AreDefaultContextMenusEnabled). Γι' αυτό εκθέτουμε
        #    Python συνάρτηση που διαβάζει το clipboard μέσω tkinter/click.
        class _Api:
            def paste_license(self):
                """Επιστρέφει το κείμενο του clipboard (ή "" αν αποτύχει)."""
                try:
                    import tkinter as tk
                    r = tk.Tk()
                    r.withdraw()
                    r.update()                      # απαραίτητο σε Windows
                    try:
                        txt = r.clipboard_get()
                    finally:
                        r.destroy()
                    return (txt or "").strip()
                except Exception:
                    return ""
            def open_url(self, u):
                """Ανοίγει εξωτερικό link στον default browser."""
                try:
                    import webbrowser
                    webbrowser.open(str(u))
                    return True
                except Exception:
                    return False

        window = webview.create_window(
            "Privacy-YouTuber",
            url,
            width=1200,
            height=800,
            min_size=(900, 600),
            hidden=True,       # ξεκινάει κρυφό → εμφανίζεται όταν φορτώσει
            background_color="#0e1116",
            js_api=_Api(),     # 🔌 window.pywebview.api.paste_license()
        )
        def _on_loaded_max():
            try:
                window.maximize()   # 🖥️ full-μεγέθους (maximized) από την αρχή
                window.show()
            except Exception:
                pass
        window.events.loaded += _on_loaded_max
        webview.start()
        # 🧹 ΚΑΘΑΡΙΣΜΟΣ: το pywebview/WebView2 αφήνει ΟΡΦΑΝΑ child processes (msedgewebview2)
        #    όταν το παράθυρο κλείσει. Χωρίς αυτό, μένουν ~400MB + 6 processes να ζεσταίνουν
        #    το μηχάνημα. Τα σκοτώνουμε ΜΟΝΟ όσα ανήκουν στο δικό μας process tree.
        _kill_orphan_webviews()
        return
    except Exception:
        # pywebview δεν υπάρχει ή απέτυχε → πέσε στον ασφαλή browser δρόμο.
        _open_private(url)


def _tk_dialog(kind, **kwargs):
    """Ανοίγει native dialog με tkinter. Επιστρέφει το μονοπάτι ή None (ακύρωση/αποτυχία).

    Τρέχει στον υπολογιστή που τρέχει ο server (ΟΧΙ στον browser), άρα δουλεύει
    το ίδιο σε Brave/Chrome/Firefox/Edge. Αν δεν υπάρχει tkinter ή δεν υπάρχει
    display (headless), επιστρέφει None.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    try:
        root = tk.Tk()
        root.withdraw()          # κρύβει το κενό κύριο παράθυρο
        root.wm_attributes("-topmost", True)  # ο dialog πάνω από όλα
        root.update()
        if kind == "save":
            result = filedialog.asksaveasfilename(parent=root, **kwargs)
        else:
            result = filedialog.askopenfilename(parent=root, **kwargs)
        root.destroy()
        return result or None
    except Exception:
        return None


def _ask_save_path(title, default_dir, default_name, filetypes):
    return _tk_dialog(
        "save",
        title=title,
        initialdir=default_dir if os.path.isdir(default_dir) else os.path.expanduser("~"),
        initialfile=default_name,
        defaultextension=".json",
        filetypes=filetypes,
    )


def _ask_open_path(title, filetypes):
    return _tk_dialog(
        "open",
        title=title,
        filetypes=filetypes,
    )


def fetch_rss(channel_id, timeout=15):
    """Τραβά και παράρει το δημόσιο RSS feed ενός καναλιού.
    Επιστρέφει λίστα [{video_id, title, channel, published}] ή None σε αποτυχία."""
    import ssl
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        ctx = ssl.create_default_context()
        raw = urllib.request.urlopen(req, timeout=timeout, context=ctx).read()
    except Exception:
        return None
    txt = raw.decode("utf-8", "replace")
    entries = re.findall(r"<entry>(.*?)</entry>", txt, re.DOTALL)
    out = []
    for e in entries:
        title = re.search(r"<title>(.*?)</title>", e, re.DOTALL)
        vid = re.search(r"<yt:videoId>(.*?)</yt:videoId>", e)
        author = re.search(r"<name>(.*?)</name>", e, re.DOTALL)
        published = re.search(r"<published>(.*?)</published>", e)
        if not vid:
            continue
        out.append({
            "video_id": vid.group(1).strip(),
            "title": (title.group(1).strip() if title else ""),
            "channel": (author.group(1).strip() if author else ""),
            "published": (published.group(1).strip() if published else ""),
        })
    return out


def fetch_channel_videos_ytdlp(channel_id, limit=30):
    """Εναλλακτική μέθοδος (failback) όταν το RSS feed είναι εκτός λειτουργίας.

    Χρησιμοποιεί το yt-dlp για να τραβήξει τα πιο πρόσφατα δημόσια βίντεο ενός
    καναλιού (flat playlist) χωρίς κατέβασμα — μόνο metadata. Επιστρέφει την
    ίδια δομή με το fetch_rss: [{video_id, title, channel, published}].

    Το import γίνεται lazy (μέσα στη συνάρτηση) ώστε η εφαρμογή να μη σπάει
    αν το yt_dlp λείπει από κάποιο περιβάλλον.
    """
    try:
        import yt_dlp
    except ImportError:
        return None
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    out = []
    try:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlistend": limit,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info or "entries" not in info:
            return None
        for e in info["entries"]:
            if not e:
                continue
            vid = e.get("id") or e.get("url")
            if not vid or len(str(vid)) != 11:
                continue
            out.append({
                "video_id": str(vid),
                "title": e.get("title") or "",
                "channel": (e.get("channel") or e.get("uploader") or ""),
                # extract_flat ΔΕΝ δίνει πάντα timestamp· η σειρά είναι ήδη νεότερα→παλιότερα.
                # Βάζουμε φθίνοντα αριθμό ως εφεδρικό «νεότερο πρώτα» κλειδί.
                "published": e.get("timestamp") or _flat_order_key(out),
            })
    except Exception:
        return None if not out else out
    return out


def _flat_order_key(existing_list):
    """Επιστρέφει ένα μοναδικό, φθίνον string όταν λείπει το timestamp,
    ώστε να διατηρείται η σειρά «νεότερα πρώτα» που ήδη δίνει το yt-dlp."""
    return f"9999999999999-{len(existing_list):05d}"


def fetch_rss_with_fallback(channel_id, timeout=15):
    """Προσπαθεί πρώτα το RSS feed· αν αποτύχει, πέφτει αυτόματα στο yt-dlp.

    Αυτή είναι η συνάρτηση που καλείται πλέον από το _check_new — έτσι η
    ανακάλυψη νέων βίντεο δεν εξαρτάται από ένα μόνο (εύθραυστο) endpoint.
    """
    rss = fetch_rss(channel_id, timeout=timeout)
    if rss is not None:
        return rss
    return fetch_channel_videos_ytdlp(channel_id)


def youtube_search(query, mode="videos", offset=0, limit=24):
    """Αναζητά το YouTube (χωρίς API key, χωρίς server).

    mode:
        "videos"   → ΜΟΝΟ βίντεο (24/σελίδα, με offset για Next)
        "channels" → ΜΟΝΟ κανάλια (24 με τη μία, χωρίς pagination)
        "both"     → 24 βίντεο + 24 κανάλια (ισορροπία)

    Επιστρέφει:
        {"videos": [...], "channels": [...], "has_more": bool}
    """
    page = max(1, int(limit or 24))
    if mode == "channels":
        videos = []
        channels = _search_channels_scrape(query, page, offset)
        has_more = len(channels) == page
    elif mode == "both":
        half = page
        # ⚡ ΠΑΡΑΛΛΗΛΑ: τα βίντεο (yt-dlp, ~2s) και τα κανάλια (scrape, ~1s) δεν
        #    εξαρτώνται το ένα από το άλλο. Σε σειρά πληρώναμε το άθροισμα
        #    (~3s+). Παράλληλα πληρώνουμε το max (~2s) — κέρδος ~1s στο UI,
        #    γιατί το JSON επιστρέφει όταν τελειώσει το πιο αργό νήμα.
        #    (Ο server είναι ThreadingHTTPServer, άρα σηκώνει 2 νήματα.)
        with ThreadPoolExecutor(max_workers=2) as _ex:
            _fut_v = _ex.submit(_search_videos, query, half, offset)
            _fut_c = _ex.submit(_search_channels_scrape, query, half, offset)
            videos = _fut_v.result() or []
            channels = _fut_c.result() or []
        has_more = (len(videos) == half) or (len(channels) == half)
    else:  # "videos" (default)
        videos = _search_videos(query, page, offset=offset)
        channels = []
        has_more = len(videos) == page
    return {"videos": videos or [], "channels": channels or [], "has_more": has_more}




def _search_videos(query, limit=20, offset=0):
    """🔎 ΔΥΟ ΣΥΡΤΑΡΙΑ ΠΑΡΑΛΛΗΛΑ: InnerTube + yt-dlp, με εναλλαγή και αποδιπλοποίηση.

    ΓΙΑΤΙ (ιδέα Ανδρίκου, μετρημένη): τα δύο συρτάρια δίνουν ΔΙΑΦΟΡΕΤΙΚΑ αποτελέσματα
    (μετρήθηκε: 26 μοναδικά από 40). Ζητώντας ΚΑΙ τα δύο παράλληλα:
      • Χρόνος = του πιο γρήγορου (1.52s) — όχι άθροισμα.
      • Διπλάσιο υλικό: 40 αντί για 20, που γεμίζει τη σελίδα πιο γρήγορα.
      • Δεν ναυαγεί αν το ένα σκάσει — το άλλο δίνει αποτέλεσματα.
    Εναλλαγή (A,B,A,B) ώστε τα αποτελέσματα να έρχονται «μακριά» μεταξύ τους,
    όπως ζήτησε ο Ανδρίκος — ΟΧΙ μαζεμένα τα μεν μετά τα δε.

    ΣΗΜΑΝΤΙΚΟ: μην ζητάς offset στη 2η σελίδα από την ΙΔΙΑ πηγή — το YouTube
    πληρώνει πρώτα την 1η σελίδα για να δώσει το continuation token (μετρήθηκε:
    offset=20 → 2.80s αντί 1.13s). Γι' αυτό βάζουμε ΤΙΣ ΔΥΟ πηγές στην 1η σελίδα.
    """
    if offset:
        # Σελιδοποίηση: πάρε από την πηγή που «αντέχει» το offset χωρίς βάρος.
        vids = _search_videos_ytdlp(query, limit, offset)
        return vids or _search_videos_innertube(query, limit, offset)

    # 1η σελίδα: ΚΑΙ ΤΑ ΔΥΟ συρτάρια παράλληλα.
    with ThreadPoolExecutor(max_workers=2) as _ex:
        _f_it = _ex.submit(_search_videos_innertube, query, limit, 0)
        _f_yt = _ex.submit(_search_videos_ytdlp, query, limit, 0)
        v_it = _f_it.result() or []
        v_yt = _f_yt.result() or []

    # 🚫 Αποδιπλοποίηση: κρατάμε την ΠΡΩΤΗ εμφάνιση κάθε video_id.
    seen, out = set(), []
    for v in v_it + v_yt:
        vid = v.get("video_id")
        if vid and vid not in seen:
            seen.add(vid)
            out.append(v)

    # 🔀 ΕΝΑΛΛΑΓΗ (A,B,A,B): ξανα-πλέκει τα δύο συρτάρια ώστε η λίστα να
    #    εναλλάσσει προελεύσεις — «μακριά» τα αποτελέσματα, όχι ομαδοποιημένα.
    if v_it and v_yt:
        seen2, mixed = set(), []
        for i in range(max(len(v_it), len(v_yt))):
            for src in (v_it, v_yt):
                if i < len(src):
                    vid = src[i].get("video_id")
                    if vid and vid not in seen2:
                        seen2.add(vid)
                        mixed.append(src[i])
        if len(mixed) >= min(len(v_it), len(v_yt)):
            return mixed[:max(limit, len(mixed))]

    return out


def _search_videos_ytdlp(query, limit=10, offset=0):
    """Ψάχνει βίντεο στο YouTube μέσω yt-dlp (ytsearch). Υποστηρίζει offset (playliststart)."""
    try:
        import yt_dlp
    except ImportError:
        return []
    out = []
    try:
        # ytsearchN τραβάει N αποτελέσματα· το playliststart κάνει «σελίδα».
        # Ζητάμε όσα χρειαζόμαστε (limit) + offset, και κόβουμε τα πρώτα offset.
        opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}
        total = limit + offset
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{total}:{query}", download=False)
        entries = info.get("entries") or []
        entries = entries[offset:offset + limit]
        for e in entries:
            if not e:
                continue
            vid = e.get("id") or ""
            if not vid or len(str(vid)) != 11:
                continue
            out.append({
                "video_id": str(vid),
                "title": e.get("title") or "",
                "channel": (e.get("channel") or e.get("uploader") or ""),
                "duration": e.get("duration") or 0,
                "views": e.get("view_count") or 0,
                "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
            })
    except Exception:
        pass
    return out


def _search_videos_innertube(query, limit=20, offset=0):
    """Ψάχνει βίντεο μέσω InnerTube (youtubei/v1/search) με φίλτρο ΜΟΝΟ βίντεο.

    ΓΙΑΤΙ: μετρημένο ~0.8-1.1s για 20 βίντεο, έναντι ~2.3s του yt-dlp (μισός χρόνος).
    Το κλειδί είναι το params "EgIQAQ==": χωρίς αυτό το YouTube γυρνάει μικτό
    feed (Shorts/ράφια/κανάλια) και μένουμε με ~10 βίντεο. Με αυτό: καθαρά βίντεο.

    Επιστρέφει την ΙΔΙΑ μορφή με το _search_videos_ytdlp, ώστε να είναι drop-in.

    offset: το YouTube δίνει ~20/σελίδα. Για offset>0 ακολουθούμε continuation
    tokens όσες φορές χρειάζεται (κάθε σελίδα ~0.3-1.0s).

    Επιστρέφει [] σε κάθε αποτυχία — ο caller πέφτει στο yt-dlp (εφεδρεία).
    """
    import json as _json, gzip as _gzip
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    HDRS = {"Content-Type": "application/json", "User-Agent": UA,
            "Accept-Encoding": "gzip", "Origin": "https://www.youtube.com",
            "X-YouTube-Client-Name": "1",
            "X-YouTube-Client-Version": "2.20240501.00.00"}
    CTX = {"client": {"clientName": "WEB", "clientVersion": "2.20240501.00.00",
                      "hl": "en", "gl": "US", "utcOffsetMinutes": 0}}
    PARAMS_VIDEO_ONLY = "EgIQAQ=="

    def _post(payload):
        body = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://www.youtube.com/youtubei/v1/search?prettyPrint=false",
            data=body, headers=HDRS)
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read()
            if (r.headers.get("Content-Encoding") or "").lower() == "gzip":
                raw = _gzip.decompress(raw)
        return _json.loads(raw.decode("utf-8", "ignore"))

    def _parse(data):
        vids, token = [], None

        def walk(o):
            nonlocal token
            if isinstance(o, dict):
                if "videoRenderer" in o:
                    v = o["videoRenderer"]
                    vid = v.get("videoId") or ""
                    dur = (v.get("lengthText") or {}).get("simpleText") or ""
                    # 🧹 ΜΟΝΟ κανονικά βίντεο: με διάρκεια (κόβει live/premieres που
                    #    εμφανίζονται ως badges χωρίς lengthText).
                    if vid and len(vid) == 11 and dur:
                        vids.append({
                            "video_id": vid,
                            "title": "".join(x.get("text", "") for x in
                                             (v.get("title") or {}).get("runs", [])),
                            "channel": (((v.get("ownerText") or {}).get("runs")
                                         or [{}])[0].get("text", "")),
                            "duration": dur,
                            "views": (v.get("viewCountText") or {}).get("simpleText", ""),
                            "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                        })
                if "continuationCommand" in o and not token:
                    t = o["continuationCommand"].get("token")
                    if t:
                        token = t
                for x in o.values():
                    walk(x)
            elif isinstance(o, list):
                for x in o:
                    walk(x)

        walk(data)
        return vids, token

    try:
        data = _post({"context": CTX, "query": query, "params": PARAMS_VIDEO_ONLY})
        vids, tok = _parse(data)
        # Σελιδοποίηση: 20/σελίδα. Πάρε offset+limit, και μετά κόψε τα πρώτα offset.
        target = max(1, int(offset or 0)) + max(1, int(limit or 20))
        guard = 0
        while len(vids) < target and tok and guard < 8:
            guard += 1
            try:
                d2 = _post({"context": CTX, "continuation": tok})
            except Exception:
                break
            more, tok = _parse(d2)
            if not more:
                break
            vids.extend(more)
        off = max(0, int(offset or 0))
        return vids[off:off + max(1, int(limit or 20))]
    except Exception:
        return []


def _search_channels_scrape(query, limit=24, offset=0):
    """Ψάχνει ΚΑΝάλια στο YouTube (results page, filter channels) με σελιδοποίηση
    μέσω continuation token. Επιστρέφει τα κανάλια της «σελίδας» offset..offset+limit."""
    import urllib.parse, urllib.request
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
    base = ("https://www.youtube.com/results?search_query="
            + urllib.parse.quote(query) + "&sp=EgIQAg%3D%3D")
    txt = _fetch_text(base, timeout=12, ua=UA)
    if not txt:
        return []

    # API key για continuation: πρώτα από το .env (YT_API_KEY), αλλιώς το γνωστό δημόσιο WEB key.
    api_key = _env("YT_API_KEY", "")
    m = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', txt)
    if m:
        api_key = m.group(1)

    def collect(data):
        out = []
        def _walk(obj):
            if isinstance(obj, dict):
                if "channelRenderer" in obj:
                    ch = obj["channelRenderer"]
                    cid = ch.get("channelId", "")
                    name = ch.get("title", {}).get("simpleText", "")
                    if cid:
                        out.append({"channel_id": cid, "name": name})
                for v in obj.values():
                    _walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    _walk(v)
        _walk(data)
        return out

    def find_token(data):
        found = []
        def _walk(obj):
            if isinstance(obj, dict):
                if "continuationCommand" in obj:
                    tok = obj["continuationCommand"].get("token", "")
                    if tok:
                        found.append(tok)
                for v in obj.values():
                    _walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    _walk(v)
        _walk(data)
        return found[0] if found else None

    channels = []
    token = None
    m = re.search(r"var ytInitialData = (\{.*?\});", txt, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
        except Exception:
            data = None
        if data:
            channels.extend(collect(data))
            token = find_token(data)

    # Σελιδοποίηση: συνέχισε μέχρι να μαζέψουμε offset + limit κανάλια.
    target = offset + limit
    seen = {c["channel_id"] for c in channels}
    while len(channels) < target and token and api_key:
        body = json.dumps({
            "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240101.00.00",
                                   "hl": "el", "gl": "GR"}},
            "continuation": token,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://www.youtube.com/youtubei/v1/search?key=" + api_key,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": UA},
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                resp = r.read().decode("utf-8", "ignore")
        except Exception:
            break
        try:
            d = json.loads(resp)
        except Exception:
            break
        new = [c for c in collect(d) if c["channel_id"] not in seen]
        if not new:
            break
        seen.update(c["channel_id"] for c in new)
        channels.extend(new)
        token = find_token(d)

    return channels[offset:offset + limit]


def channel_preview(channel_id):
    """Συγκεντρώνει ό,τι χρειάζεται το eye window ενός καναλιού:
    όνομα, avatar URL, και τα πρόσφατα βίντεο (χωρίς API key/server).

    Επιστρέφει:
        {"channel_id", "name", "avatar", "videos": [{"video_id","title","thumb"}...]}
    """
    name = ""
    avatar = f"https://yt3.googleusercontent.com/channel/{channel_id}"
    # Προσπάθησε για το κανονικό όνομα + avatar από το channel page (og:)
    html = _fetch_text(
        f"https://www.youtube.com/channel/{channel_id}",
        timeout=10,
        ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )
    if html:
        m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if m:
            name = m.group(1).strip()
        m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if m:
            avatar = m.group(1)
    if not name:
        name = channel_id
    videos = []
    for v in (fetch_channel_videos_ytdlp(channel_id, limit=10) or []):
        videos.append({
            "video_id": v.get("video_id"),
            "title": v.get("title", ""),
            "thumb": f"https://i.ytimg.com/vi/{v.get('video_id')}/mqdefault.jpg",
        })
    return {"channel_id": channel_id, "name": name, "avatar": avatar, "videos": videos}


def _warm_imports():
    """Προθέρμανση βαριών modules στο background ΜΕΤΑ την εκκίνηση του UI,
    ώστε το πρώτο search / πρώτο thumbnail-χρώμα να μην πληρώσει το import."""
    for name in ("PIL.Image", "yt_dlp"):
        try:
            __import__(name)
        except Exception:
            pass


def serve(open_browser=False):
    db.init()
    threading.Thread(target=_warm_imports, daemon=True).start()
    srv, port = _bind_server(HOST, PORT)
    # cache-busting: μοναδικό query param ώστε ο WebView2 να ΜΗΝ φορτώσει stale HTML.
    url = f"http://{HOST}:{port}/?v={int(datetime.now().timestamp())}"
    print(f"🔒 Privacy-YouTuber listening on {url}")
    print("   Άφησέ το να τρέχει. Ctrl+C για τερματισμό.")
    if open_browser:
        # ο server πρέπει να τρέχει σε daemon thread, γιατί το pywebview
        # (WinForms/WebView2) ΑΠΑΙΤΕΙ το main thread. Ο browser fallback μένει.
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            _open_window(url)   # blocking στο MAIN thread (σωστό για pywebview)
        except KeyboardInterrupt:
            print("\n👋 Τερματισμός.")
        return
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Τερματισμός.")


def _bind_server(host, start_port):
    """Δένει τον server στο start_port· αν είναι κατειλημμένο, δοκιμάζει τα επόμενα ports
    (start_port+1, +2, ...) μέχρι να βρει ελεύθερο. Ποτέ δεν «αρνείται» — πάντα ξεκινά.
    Επιστρέφει (srv, port) ώστε ο browser να ανοίξει στο ΣΩΣΤΟ port."""

    class _ExclusiveServer(ThreadingHTTPServer):
        # ΑΠΕΝΕΡΓΟΠΟΙΟΥΜΕ το allow_reuse_address αλλιώς δύο processes δένουν στο ΙΔΙΟ port
        # (SO_REUSEADDR) χωρίς σφάλμα — και ο browser μπλέκεται ανάμεσα σε servers.
        allow_reuse_address = False

    for offset in range(20):
        port = start_port + offset
        try:
            srv = _ExclusiveServer((host, port), Handler)
            return srv, port
        except OSError as e:
            # address already in use → δοκίμασε το επόμενο port
            if offset == 19:
                # έσχατη λύση: άφησε το OS να διαλέξει ελεύθερο port (0)
                srv = _ExclusiveServer((host, 0), Handler)
                return srv, srv.server_address[1]
            continue


if __name__ == "__main__":
    serve(open_browser=True)
