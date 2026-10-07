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
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import db, recommender

PORT = 8765
HOST = "127.0.0.1"  # δέχεται ΜΟΝΟ τοπικές συνδέσεις — ποτέ από το internet

# 📦 Η τρέχουσα έκδοση του app. Το auto-update τη συγκρίνει με το latest.json.
VERSION = "1.0.0"

# 📦 Πού ψάχνει το app για ενημερώσεις (GitHub raw). Public repo απαραίτητο.
UPDATE_URL = "https://raw.githubusercontent.com/andyspartintrade/PrivacyYouTuber/main/latest.json"


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


def _cached_file(subdir, key, ext=".jpg"):
    """Επιστρέφει το path ενός cached αρχείου (χωρίς να το κατεβάσει)."""
    d = os.path.join(db.data_dir(), subdir)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{key}{ext}")


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


def _is_embeddable_cached(video_id, timeout=1.2):
    """Γρήγορος, cached έλεγχος embeddable (για φιλτράρισμα feed χωρίς spam στο δίκτυο).

    Επιστρέφει True (παίζει), False (μπλοκαρισμένο), ή True (fail-open αν άγνωστο/timeout).
    """
    cached = db.get_embeddable(video_id)
    if cached is not None:
        return bool(cached)
    # όχι στη cache → έλεγξε με μικρό timeout
    try:
        url = (
            "https://www.youtube.com/oembed?url="
            + urllib.parse.quote("https://www.youtube.com/watch?v=" + video_id)
            + "&format=json"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = (resp.status == 200)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            result = False
        else:
            result = True   # fail-open
    except Exception:
        result = True       # fail-open (δεν κρύβουμε αν δεν ξέρουμε)
    db.set_embeddable(video_id, result)
    return result


def filter_embeddable(video_ids):
    """Από μια λίστα video_id, κρατάει ΜΟΝΟ όσα επιτρέπουν embed (παράλληλα + cached)."""
    from concurrent.futures import ThreadPoolExecutor
    if not video_ids:
        return []
    with ThreadPoolExecutor(max_workers=8) as ex:
        flags = list(ex.map(_is_embeddable_cached, video_ids))
    return [vid for vid, ok in zip(video_ids, flags) if ok]



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
        self.send_header("Access-Control-Allow-Origin", "*")
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
        }

    def _dashboard(self):
        vids = db.all_videos()
        stats = db.stats()
        topics = recommender.top_terms(vids, n=12) if vids else []
        ui = db.get_ui_state()
        recent = [self._video_payload(v) for v in vids[:200]]
        self._json(200, {
            "stats": stats,
            "topics": topics,
            "videos": recent,
            "all_tags": db.all_tags(),
            "channel_tags": db.channel_tags_map(),
            "all_categories": db.all_categories(),
            "channel_watch": db.all_channel_watch(),
            "channel_watch_meta": db.channel_watch_meta(),
            "collapsed": ui.get("collapsed", []),
            "order": ui.get("order", []),
            "cat_order": ui.get("cat_order", []),
            "cat_collapsed": ui.get("cat_collapsed", []),
            "rss_shown": ui.get("rss_shown", 6),
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

    def _serve_thumb(self, video_id):
        path = get_thumbnail(video_id)
        if not path:
            self._json(404, {"error": "no thumbnail"})
            return
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_avatar(self, channel_id):
        path = get_channel_avatar(channel_id)
        if not path:
            self._json(404, {"error": "no avatar"})
            return
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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
            with open(os.path.join(_web_dir(), "index.html"), encoding="utf-8") as f:
                self._html(200, f.read())
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
                })
            except Exception as e:
                self._json(200, {"ok": False, "error": str(e), "current": VERSION})
        elif path == "/api/recent-searches":
            self._json(200, {"searches": db.get_recent_searches()})
        elif path == "/api/video-notes":
            vid = parse_qs(parsed.query).get("video_id", [""])[0]
            self._json(200, {"notes": db.get_video_notes(vid)})
        elif path == "/api/all-video-notes":
            ids = parse_qs(parsed.query).get("ids", [""])[0].split(",")
            ids = [i for i in ids if i]
            self._json(200, {"notes": db.video_notes_for_videos(ids)})
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
            st = {
                "collapsed": data.get("collapsed") or [],
                "order": data.get("order") or [],
                "cat_order": data.get("cat_order") or [],
                "cat_collapsed": data.get("cat_collapsed") or [],
            }
            if "rss_shown" in data and isinstance(data["rss_shown"], int) and data["rss_shown"] >= 1:
                st["rss_shown"] = data["rss_shown"]
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
            limit = int(data.get("limit", 10) or 10)
            mode = (data.get("mode") or "videos").strip()
            offset = int(data.get("offset", 0) or 0)
            res = youtube_search(q, mode=mode, offset=offset)
            videos = res["videos"]
            # 🧹 Φιλτράρισε non-embeddable (παίζουν μόνο όσα επιτρέπουν embed) — cached/fail-open.
            if videos:
                vids_ids = [v["video_id"] for v in videos]
                ok_ids = set(filter_embeddable(vids_ids))
                videos = [v for v in videos if v["video_id"] in ok_ids]
                # διορθώνουμε το has_more αν φιλτράραμε πολλά
            self._json(200, {"ok": True, "videos": videos, "channels": res["channels"], "has_more": res["has_more"]})
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
        elif path == "/dismiss_video":
            db.dismiss_video(data.get("video_id"))
            self._json(200, {"ok": True})
        elif path == "/add":
            vid = extract_video_id(data.get("url", ""))
            if not vid:
                self._json(400, {"ok": False, "error": "Δεν κατάλαβα το link — δώσε ένα YouTube URL."})
                return
            info = scrape_video_info(vid) or {}
            # ✅ Οποιοδήποτε ➕ (URL, search, feed, window) = ΕΓΚΡΙΝΕΤΑΙ ΑΜΕΣΩΣ.
            # Δεν υπάρχει πια «υπό έγκριση»/ΝΕΟ για χειροκίνητη προσθήκη.
            # Αν το frontend στέλνει channel_id/channel (από feed), τα εμπιστευόμαστε
            # αντί να βασιστούμε στο scrape (γρηγορότερο + δεν χάνει το κανάλι).
            cid = (data.get("channel_id") or "").strip() or info.get("channel_id")
            chname = (data.get("channel") or "").strip() or info.get("channel")
            db.record_watch({
                "video_id": vid,
                "title": info.get("title") or vid,
                "channel": chname,
                "channel_id": cid,
                "unseen": False,
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
            subprocess.Popen([p, "--incognito", url])
            return
    chrome = shutil.which("chrome.exe") or shutil.which("chrome") or shutil.which("google-chrome")
    if chrome:
        subprocess.Popen([chrome, "--incognito", url])
        return
    edge = shutil.which("msedge.exe")
    if edge:
        subprocess.Popen([edge, "--inprivate", url])
        return
    webbrowser.open(url)


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
        window = webview.create_window(
            "Privacy-YouTuber",
            url,
            width=1200,
            height=800,
            min_size=(900, 600),
            hidden=True,       # ξεκινάει κρυφό → εμφανίζεται όταν φορτώσει
            background_color="#0e1116",
        )
        def _on_loaded_max():
            try:
                window.maximize()   # 🖥️ full-μεγέθους (maximized) από την αρχή
                window.show()
            except Exception:
                pass
        window.events.loaded += _on_loaded_max
        webview.start()
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


def youtube_search(query, mode="videos", offset=0):
    """Αναζητά το YouTube (χωρίς API key, χωρίς server).

    mode:
        "videos"   → ΜΟΝΟ βίντεο (50/σελίδα, με offset για Next)
        "channels" → ΜΟΝΟ κανάλια (50 με τη μία, χωρίς pagination)
        "both"     → 25 βίντεο + 25 κανάλια (ισορροπία)

    Επιστρέφει:
        {"videos": [...], "channels": [...], "has_more": bool}
    """
    page = 50
    if mode == "channels":
        videos = []
        channels = _search_channels_scrape(query, page)
        has_more = False          # κανάλια: χωρίς Next (best-effort stability)
    elif mode == "both":
        half = 25
        videos = _search_videos_ytdlp(query, half, offset=offset)
        channels = _search_channels_scrape(query, half)
        has_more = len(videos) == half
    else:  # "videos" (default)
        videos = _search_videos_ytdlp(query, page, offset=offset)
        channels = []
        has_more = len(videos) == page
    return {"videos": videos or [], "channels": channels or [], "has_more": has_more}


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


def _search_channels_scrape(query, limit=10):
    """Ψάχνει ΚΑΝάλια στο YouTube (results page, filter channels) και
    τα παράρει από το ytInitialData JSON."""
    import urllib.parse
    url = ("https://www.youtube.com/results?search_query="
           + urllib.parse.quote(query) + "&sp=EgIQAg%3D%3D")
    txt = _fetch_text(url, timeout=12, ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0")
    if not txt:
        return []
    m = re.search(r"var ytInitialData = (\{.*?\});", txt, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except Exception:
        return []
    channels = []

    def _walk(obj):
        if isinstance(obj, dict):
            if "channelRenderer" in obj:
                ch = obj["channelRenderer"]
                cid = ch.get("channelId", "")
                name = ch.get("title", {}).get("simpleText", "")
                if cid:
                    channels.append({"channel_id": cid, "name": name})
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)

    _walk(data)
    return channels[:limit]


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


def serve(open_browser=False):
    db.init()
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
