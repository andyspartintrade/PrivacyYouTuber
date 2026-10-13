"""SQLite — όλη η τοπική αποθήκευση του Privacy-YouTuber.

Δύο πίνακες:
  videos       — ένας ανά βίντεο (dedupe με video_id), με μετρητή watch_count.
  watch_events — ένα γεγονός ανά προβολή (για μελλοντικά analytics).

Μηδέν εξαρτήσεις, μόνο stdlib.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone


def data_dir():
    """Μόνιμος φάκελος δεδομένων — διαφορετικός για κανονική vs packaged εκτέλεση."""
    if getattr(sys, "frozen", False):
        # PyInstaller: γράψε σε %LOCALAPPDATA%\PrivacyYouTuber (επιζεί από runs).
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "PrivacyYouTuber")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


DB_PATH = os.path.join(data_dir(), "privacy_yt.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    video_id        TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    channel         TEXT,
    channel_id      TEXT,
    description     TEXT,
    category        TEXT,
    user_category   TEXT,
    tags            TEXT,          -- JSON array (metadata YouTube)
    my_tags         TEXT DEFAULT '[]',   -- προσωπικά tags χρήστη (JSON array)
    rating          INTEGER DEFAULT 0,   -- 0-5 αστεράκια χρήστη
    first_seen_at   TEXT,
    last_watched_at TEXT,
    watch_count     INTEGER DEFAULT 1,
    rank            INTEGER DEFAULT 0,
    pinned          INTEGER DEFAULT 0,
    unseen          INTEGER DEFAULT 0,  -- 1 = προστέθηκε με ➕ αλλά ΔΕΝ έχει ειδωθεί ακόμα
    is_embeddable   INTEGER             -- 1 = embed OK, 0 = owner μπλόκαρε embed, NULL = άγνωστο
);

CREATE TABLE IF NOT EXISTS watch_events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id         TEXT NOT NULL,
    watched_at       TEXT NOT NULL,
    duration_seconds REAL,
    FOREIGN KEY (video_id) REFERENCES videos (video_id)
);

CREATE TABLE IF NOT EXISTS channel_tags (
    channel_id      TEXT PRIMARY KEY,
    tags            TEXT DEFAULT '[]'   -- προσωπικά tags καναλιού (JSON array)
);

CREATE TABLE IF NOT EXISTS ui_state (
    key             TEXT PRIMARY KEY,
    value           TEXT                 -- JSON (collapsed/order, κλπ)
);

CREATE TABLE IF NOT EXISTS categories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    created_at      TEXT
);

CREATE TABLE IF NOT EXISTS tag_stats (
    tag             TEXT PRIMARY KEY,
    use_count       INTEGER DEFAULT 0,
    last_used_at    TEXT
);

CREATE TABLE IF NOT EXISTS channel_watch (
    channel_id      TEXT PRIMARY KEY,
    enabled         INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS dismissed (
    video_id        TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS recent_searches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    query           TEXT NOT NULL,
    searched_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS video_notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id        TEXT NOT NULL,
    title           TEXT DEFAULT '',
    note            TEXT DEFAULT '',
    timestamp_sec   INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);

-- 🔍 Cache αποτελεσμάτων αναζήτησης (ανά query+mode): ώστε το «Επόμενα» να είναι ακαριαίο.
--    Το position κρατά τη ΣΕΙΡΑ που έδωσε το YouTube (0 = πρώτο αποτέλεσμα).
CREATE TABLE IF NOT EXISTS search_cache (
    query           TEXT NOT NULL,
    mode            TEXT NOT NULL,
    position        INTEGER NOT NULL,
    video_id        TEXT,
    title           TEXT DEFAULT '',
    channel         TEXT DEFAULT '',
    channel_id      TEXT DEFAULT '',
    duration        INTEGER DEFAULT 0,
    views           INTEGER DEFAULT 0,
    cached_at       TEXT NOT NULL,
    PRIMARY KEY (query, mode, position)
);

CREATE TABLE IF NOT EXISTS channel_videos_cache (
    channel_id      TEXT NOT NULL,
    video_id        TEXT NOT NULL,
    title           TEXT DEFAULT '',
    position        INTEGER DEFAULT 0,   -- σειρά (0 = νεότερο)
    cached_at       TEXT NOT NULL,
    PRIMARY KEY (channel_id, video_id)
);
"""


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout = 5000")  # να μην κλειδώνει με το ασύγχρονο backfill
    return c


def init():
    with _conn() as c:
        c.executescript(SCHEMA)
        # Migration: πρόσθεσε στήλες σε βάσεις που δημιουργήθηκαν με παλιό σχήμα.
        cols = [r[1] for r in c.execute("PRAGMA table_info(videos)").fetchall()]
        if "channel_id" not in cols:
            c.execute("ALTER TABLE videos ADD COLUMN channel_id TEXT")
        if "user_category" not in cols:
            c.execute("ALTER TABLE videos ADD COLUMN user_category TEXT")
        if "rank" not in cols:
            c.execute("ALTER TABLE videos ADD COLUMN rank INTEGER DEFAULT 0")
        if "pinned" not in cols:
            c.execute("ALTER TABLE videos ADD COLUMN pinned INTEGER DEFAULT 0")
        if "my_tags" not in cols:
            c.execute("ALTER TABLE videos ADD COLUMN my_tags TEXT DEFAULT '[]'")
        if "rating" not in cols:
            c.execute("ALTER TABLE videos ADD COLUMN rating INTEGER DEFAULT 0")
        if "unseen" not in cols:
            c.execute("ALTER TABLE videos ADD COLUMN unseen INTEGER DEFAULT 0")
        if "is_embeddable" not in cols:
            c.execute("ALTER TABLE videos ADD COLUMN is_embeddable INTEGER")
        if "pin_top" not in cols:
            c.execute("ALTER TABLE videos ADD COLUMN pin_top INTEGER DEFAULT 0")
        if "cat_rank" not in cols:
            c.execute("ALTER TABLE videos ADD COLUMN cat_rank INTEGER DEFAULT 0")
        # channel_watch: πρόσθεσε στήλη name (για εισαγμένα subscriptions).
        wcols = [r[1] for r in c.execute("PRAGMA table_info(channel_watch)").fetchall()]
        if "name" not in wcols:
            c.execute("ALTER TABLE channel_watch ADD COLUMN name TEXT")
        # ⚡ Cache embeddable ΑΝΕΞΑΡΤΗΤΗ από τον πίνακα videos — ώστε να θυμάται και βίντεο
        #    που βρέθηκαν στην αναζήτηση (δεν είναι στη βιβλιοθήκη, άρα το UPDATE videos δεν έπιανε).
        c.execute(
            "CREATE TABLE IF NOT EXISTS embeddable_cache ("
            " video_id TEXT PRIMARY KEY, ok INTEGER NOT NULL, checked_at TEXT NOT NULL)"
        )
        # ⚡ Indexes: κάνουν γρήγορα τα lookups ανά κανάλι/κατηγορία/βίντεο (πριν: full scan).
        for _idx in (
            "CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_videos_usercat ON videos(user_category)",
            "CREATE INDEX IF NOT EXISTS idx_events_video ON watch_events(video_id)",
            "CREATE INDEX IF NOT EXISTS idx_notes_video ON video_notes(video_id)",
        ):
            try:
                c.execute(_idx)
            except Exception:
                pass


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def record_watch(event):
    """Καταγράφει (ή ενημερώνει) ένα βίντεο από το payload του extension."""
    vid = event.get("video_id")
    if not vid:
        return
    # 🔒 Fallback: αν λείπει το όνομα καναλιού, χρησιμοποίησε το channel_id — ΠΟΤΕ κενό
    #    (αλλιώς «Άγνωστο κανάλι» και, παλαιότερα, το COALESCE έσβηνε υπάρχοντα ονόματα).
    _ch = (event.get("channel") or "").strip()
    _cid = (event.get("channel_id") or "").strip()
    if not _ch and _cid:
        _ch = _cid
    event = dict(event, channel=_ch)
    now = now_iso()
    with _conn() as c:
        exists = c.execute(
            "SELECT watch_count FROM videos WHERE video_id = ?", (vid,)
        ).fetchone()
        if exists:
            c.execute(
                """
                UPDATE videos
                SET last_watched_at = ?,
                    watch_count      = watch_count + 1,
                    title            = COALESCE(NULLIF(?, ''), title),
                    channel          = COALESCE(NULLIF(?, ''), channel),
                    channel_id       = COALESCE(NULLIF(?, ''), channel_id),
                    unseen           = ?
                WHERE video_id = ?
                """,
                (now, event.get("title", ""), event.get("channel"), event.get("channel_id"),
                 1 if event.get("unseen") else 0, vid),
            )
        else:
            c.execute(
                """
                INSERT INTO videos
                    (video_id, title, channel, channel_id, description, category, tags,
                     first_seen_at, last_watched_at, unseen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vid,
                    event.get("title", ""),
                    event.get("channel"),
                    event.get("channel_id"),
                    event.get("description", ""),
                    event.get("category"),
                    json.dumps(event.get("tags", []), ensure_ascii=False),
                    now,
                    now,
                    1 if event.get("unseen") else 0,
                ),
            )
        c.execute(
            "INSERT INTO watch_events (video_id, watched_at, duration_seconds) VALUES (?, ?, ?)",
            (vid, now, event.get("duration_seconds")),
        )


def import_watch(video_id, title, channel, watched_at):
    """Εισαγωγή από Takeout — σέβεται τα ΠΡΑΓΜΑΤΙΚΑ timestamps, όχι το «τώρα»."""
    if not video_id:
        return
    ts = watched_at or now_iso()
    with _conn() as c:
        row = c.execute(
            "SELECT first_seen_at, last_watched_at, watch_count FROM videos WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        if row:
            first = min(row["first_seen_at"] or ts, ts)
            last = max(row["last_watched_at"] or ts, ts)
            c.execute(
                """
                UPDATE videos
                SET first_seen_at = ?, last_watched_at = ?, watch_count = watch_count + 1,
                    title = COALESCE(NULLIF(?, ''), title), channel = COALESCE(?, channel)
                WHERE video_id = ?
                """,
                (first, last, title, channel, video_id),
            )
        else:
            c.execute(
                """
                INSERT INTO videos
                    (video_id, title, channel, description, category, tags,
                     first_seen_at, last_watched_at)
                VALUES (?, ?, ?, '', '', '[]', ?, ?)
                """,
                (video_id, title, channel, ts, ts),
            )
        c.execute(
            "INSERT INTO watch_events (video_id, watched_at) VALUES (?, ?)",
            (video_id, ts),
        )


def all_videos():
    with _conn() as c:
        rows = c.execute(
            "SELECT *, user_category AS category FROM videos ORDER BY rank DESC, last_watched_at DESC"
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            # Ρητά: το JS περιμένει «category» = Η δική μας κατηγορία (user_category),
            # ΟΧΙ τα metadata του YouTube (που είναι η στήλη category). Τα κρατάμε ξεχωριστά.
            d["category"] = d.get("user_category") or ""
            out.append(d)
        return out


def delete_video(video_id):
    """Διαγράφει ένα βίντεο (και τα events του) ΚΑΙ το απορρίπτει μόνιμα (dismissed).

    Δηλαδή: − από την κεντρική λίστα = «δεν το θέλω» → δεν ξαναπροτείνεται ποτέ
    από το RSS feed (όπως το × εκεί). Μια λογική & μία ερώτηση λιγότερη για τον χρήστη.
    """
    with _conn() as c:
        c.execute("DELETE FROM watch_events WHERE video_id = ?", (video_id,))
        c.execute("DELETE FROM videos WHERE video_id = ?", (video_id,))
    dismiss_video(video_id)


def delete_channel(channel_id):
    """Αφαιρεί ΕΝΤΕΛΩΣ ένα κανάλι: όλα τα βίντεό του + το watch flag + tags + events.

    Λειτουργεί και για κανάλια ΜΕ βίντεο (σβήνει και τα βίντεο) και για
    εισαγμένα «παρακολουθούμενα» χωρίς βίντεο (απλά βγάζει το watch).
    """
    channel_id = (channel_id or "").strip()
    if not channel_id:
        return
    with _conn() as c:
        # βρες τα βίντεο του καναλιού (με channel_id Ή με το ίδιο το channel name = fallback)
        rows = c.execute(
            "SELECT video_id FROM videos WHERE channel_id = ?", (channel_id,)
        ).fetchall()
        for r in rows:
            vid = r["video_id"]
            c.execute("DELETE FROM watch_events WHERE video_id = ?", (vid,))
            c.execute("DELETE FROM videos WHERE video_id = ?", (vid,))
        # αφαίρεσε το watch flag
        c.execute("DELETE FROM channel_watch WHERE channel_id = ?", (channel_id,))
        c.execute("DELETE FROM channel_tags WHERE channel_id = ?", (channel_id,))


def update_video_meta(video_id, channel_id=None, channel=None, title=None):
    """Ενημερώνει metadata που έλειπαν (για backfill)."""
    with _conn() as c:
        if channel_id:
            c.execute("UPDATE videos SET channel_id = ? WHERE video_id = ?", (channel_id, video_id))
        if channel:
            c.execute(
                "UPDATE videos SET channel = ? WHERE video_id = ? AND (channel IS NULL OR channel = '')",
                (channel, video_id),
            )
        if title:
            c.execute(
                "UPDATE videos SET title = ? WHERE video_id = ? AND (title IS NULL OR title = '' OR title = 'YouTube')",
                (title, video_id),
            )


def set_pin(video_id, state):
    """Καρφιτσώνει ένα βίντεο με 3 καταστάσεις:
       state = 0 → unpinned (καθόλου)
       state = 1 → in-place (καρφιτσωμένο στη θέση του)
       state = 2 → top (πάνω-πάνω)
    Επιστρέφει τη νέα κατάσταση."""
    with _conn() as c:
        cur = c.execute("SELECT pinned FROM videos WHERE video_id = ?", (video_id,)).fetchone()
        if not cur:
            return 0
        if state == 2:
            mx = c.execute("SELECT COALESCE(MAX(rank), 0) FROM videos").fetchone()[0]
            c.execute("UPDATE videos SET pinned = 1, pin_top = 1, rank = ? WHERE video_id = ?", (mx + 1, video_id))
        elif state == 1:
            c.execute("UPDATE videos SET pinned = 1, pin_top = 0 WHERE video_id = ?", (video_id,))
        else:
            c.execute("UPDATE videos SET pinned = 0, pin_top = 0 WHERE video_id = ?", (video_id,))
        return state


def toggle_pin_channel(channel_id):
    """Toggle pin για όλο το κανάλι. Επιστρέφει τη νέα κατάσταση (1/0)."""
    with _conn() as c:
        cur = c.execute(
            "SELECT pinned FROM videos WHERE channel_id = ? LIMIT 1", (channel_id,)
        ).fetchone()
        if not cur:
            return 0
        new = 0 if cur["pinned"] else 1
        c.execute("UPDATE videos SET pinned = ? WHERE channel_id = ?", (new, channel_id))
        return new


def toggle_pin(video_id):
    """Καρφιτσώνει (pin) ή ξεκαρφιτσώνει ένα βίντεο. Επιστρέφει τη νέα κατάσταση (1/0)."""
    with _conn() as c:
        cur = c.execute("SELECT pinned FROM videos WHERE video_id = ?", (video_id,)).fetchone()
        if not cur:
            return 0
        new = 0 if cur[0] else 1
        if new:
            mx = c.execute("SELECT COALESCE(MAX(rank), 0) FROM videos").fetchone()[0]
            c.execute("UPDATE videos SET pinned = 1, rank = ? WHERE video_id = ?", (mx + 1, video_id))
        else:
            c.execute("UPDATE videos SET pinned = 0 WHERE video_id = ?", (video_id,))
        return new


def reorder_videos(ordered_ids):
    """Ενημερώνει τα ranks σύμφωνα με τη σειρά που δίνει ο χρήστης (drag & drop)."""
    with _conn() as c:
        n = len(ordered_ids)
        for i, vid in enumerate(ordered_ids):
            c.execute("UPDATE videos SET rank = ? WHERE video_id = ?", (n - i, vid))


def reorder_cat_videos(ordered_ids):
    """Ενημερώνει τα cat_rank (ξεχωριστή σειρά για ΚΑΤΗΓΟΡΙΕΣ — ΔΕΝ μπλέκεται με το rank των καναλιών)."""
    with _conn() as c:
        n = len(ordered_ids)
        for i, vid in enumerate(ordered_ids):
            c.execute("UPDATE videos SET cat_rank = ? WHERE video_id = ?", (n - i, vid))


def count_videos():
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM videos").fetchone()[0]


def stats():
    """Συγκεντρωτικά νούμερα για το dashboard."""
    with _conn() as c:
        videos = c.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        events = c.execute("SELECT COUNT(*) FROM watch_events").fetchone()[0]
        top = c.execute(
            "SELECT channel, COUNT(*) AS n FROM videos "
            "WHERE channel IS NOT NULL AND channel != '' "
            "GROUP BY channel ORDER BY n DESC LIMIT 1"
        ).fetchone()
        # 🔧 ΣΩΣΤΟ μέτρημα καναλιών: COUNT(DISTINCT COALESCE(channel_id, channel))
        #    — ταυτίζεται με το πώς ομαδοποιεί το frontend (key = channel_id || channel).
        #    (Το σκέτο COUNT(DISTINCT channel) έδινε 106 αντί 104, γιατί μετρούσε
        #    διαφορετικά ΟΝΟΜΑΤΑ του ίδιου channel_id ξεχωριστά.)
        channels = c.execute(
            "SELECT COUNT(DISTINCT COALESCE(channel_id, channel)) FROM videos "
            "WHERE COALESCE(channel_id, channel) IS NOT NULL "
            "AND COALESCE(channel_id, channel) != ''"
        ).fetchone()[0]
    return {
        "videos": videos,
        "events": events,
        "top_channel": top["channel"] if top else None,
        "top_channel_count": top["n"] if top else 0,
        "channel_count": channels,
    }


def set_video_tags(video_id, tags):
    """Ορίζει τα προσωπικά tags ενός βίντεο (list)."""
    with _conn() as c:
        c.execute(
            "UPDATE videos SET my_tags = ? WHERE video_id = ?",
            (json.dumps(tags, ensure_ascii=False), video_id),
        )


def set_video_rating(video_id, rating):
    """Ορίζει το rating (0-5) ενός βίντεο."""
    with _conn() as c:
        c.execute(
            "UPDATE videos SET rating = ? WHERE video_id = ?",
            (rating, video_id),
        )


def mark_video_seen(video_id):
    """Μαρκάρει ένα βίντεο ως «ανοιγμένο» (last_watched_at) — ΔΕΝ ξεμοβίζει το ΝΕΟ (unseen αλλάζει χειροκίνητα)."""
    with _conn() as c:
        c.execute(
            "UPDATE videos SET last_watched_at = COALESCE(last_watched_at, ?) WHERE video_id = ?",
            (now_iso(), video_id),
        )


def mark_video_unseen_off(video_id):
    """Ξεμοβίζει χειροκίνητα το «ΝΕΟ» (unseen=0) — καλείται από το κουμπί «✓ το είδα»."""
    with _conn() as c:
        c.execute(
            "UPDATE videos SET unseen = 0 WHERE video_id = ?",
            (video_id,),
        )


def set_embeddable(video_id, ok):
    """Αποθηκεύει αν ένα βίντεο επιτρέπει embed (1=ναι, 0=όχι) — και στη βιβλιοθήκη και στη cache."""
    set_embeddable_many({video_id: ok})


def set_embeddable_many(results):
    """Batch: {video_id: bool}. ΜΙΑ σύνδεση/συναλλαγή για όλα (αντί για μία ανά βίντεο)."""
    if not results:
        return
    now = now_iso()
    with _conn() as c:
        c.executemany(
            "INSERT INTO embeddable_cache (video_id, ok, checked_at) VALUES (?, ?, ?) "
            "ON CONFLICT(video_id) DO UPDATE SET ok = excluded.ok, checked_at = excluded.checked_at",
            [(vid, 1 if ok else 0, now) for vid, ok in results.items()],
        )
        c.executemany(
            "UPDATE videos SET is_embeddable = ? WHERE video_id = ?",
            [(1 if ok else 0, vid) for vid, ok in results.items()],
        )


def get_embeddable_many(video_ids):
    """Batch: επιστρέφει {video_id: bool} ΜΟΝΟ για όσα ξέρουμε ήδη. ΕΝΑ query."""
    ids = [v for v in video_ids if v]
    if not ids:
        return {}
    out = {}
    with _conn() as c:
        for i in range(0, len(ids), 500):          # όριο μεταβλητών SQLite
            chunk = ids[i:i + 500]
            q = ",".join("?" for _ in chunk)
            for r in c.execute(f"SELECT video_id, ok FROM embeddable_cache WHERE video_id IN ({q})", chunk):
                out[r[0]] = bool(r[1])
            missing = [v for v in chunk if v not in out]
            if missing:
                q2 = ",".join("?" for _ in missing)
                for r in c.execute(
                    f"SELECT video_id, is_embeddable FROM videos WHERE is_embeddable IS NOT NULL AND video_id IN ({q2})",
                    missing,
                ):
                    out[r[0]] = bool(r[1])
    return out


def get_embeddable(video_id):
    """Επιστρέφει True/False/None (άγνωστο) για το embed status."""
    return get_embeddable_many([video_id]).get(video_id)


def set_channel_tags(channel_id, tags):
    """Ορίζει τα προσωπικά tags ενός καναλιού (list)."""
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO channel_tags (channel_id, tags) VALUES (?, ?)",
            (channel_id, json.dumps(tags, ensure_ascii=False)),
        )


def all_tags():
    """Όλα τα προσωπικά tags (video-level + channel-level), ταξινομημένα."""
    tags = set()
    with _conn() as c:
        for r in c.execute("SELECT my_tags FROM videos WHERE my_tags IS NOT NULL").fetchall():
            try:
                tags.update(json.loads(r[0] or "[]"))
            except Exception:
                pass
        for r in c.execute("SELECT tags FROM channel_tags WHERE tags IS NOT NULL").fetchall():
            try:
                tags.update(json.loads(r[0] or "[]"))
            except Exception:
                pass
    return sorted(tags)


def delete_tag(tag):
    """Διαγράφει ένα tag από ΟΛΑ τα βίντεο και κανάλια που το χρησιμοποιούν."""
    with _conn() as c:
        # Από τα βίντεο
        for r in c.execute("SELECT video_id, my_tags FROM videos WHERE my_tags IS NOT NULL").fetchall():
            try:
                lst = json.loads(r["my_tags"] or "[]")
            except Exception:
                lst = []
            if tag in lst:
                lst = [t for t in lst if t != tag]
                c.execute(
                    "UPDATE videos SET my_tags = ? WHERE video_id = ?",
                    (json.dumps(lst, ensure_ascii=False), r["video_id"]),
                )
        # Από τα κανάλια
        for r in c.execute("SELECT channel_id, tags FROM channel_tags WHERE tags IS NOT NULL").fetchall():
            try:
                lst = json.loads(r["tags"] or "[]")
            except Exception:
                lst = []
            if tag in lst:
                lst = [t for t in lst if t != tag]
                c.execute(
                    "UPDATE channel_tags SET tags = ? WHERE channel_id = ?",
                    (json.dumps(lst, ensure_ascii=False), r["channel_id"]),
                )


def channel_tags_map():
    """channel_id -> list of προσωπικά tags."""
    out = {}
    with _conn() as c:
        for r in c.execute("SELECT channel_id, tags FROM channel_tags").fetchall():
            try:
                out[r["channel_id"]] = json.loads(r["tags"] or "[]")
            except Exception:
                out[r["channel_id"]] = []
    return out


def get_ui_state():
    """Επιστρέφει {collapsed: [...], order: [...]} από τη βάση."""
    with _conn() as c:
        r = c.execute("SELECT value FROM ui_state WHERE key = 'ui'").fetchone()
    if r:
        try:
            return json.loads(r[0])
        except Exception:
            return {}
    return {}


def set_ui_state(state):
    """Αποθηκεύει {collapsed: [...], order: [...]} στη βάση."""
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO ui_state (key, value) VALUES ('ui', ?)",
            (json.dumps(state, ensure_ascii=False),),
        )


def get_key(key):
    """Γενικό key-value store στη βάση (για license state κλπ). Επιστρέφει dict ή None."""
    with _conn() as c:
        r = c.execute("SELECT value FROM ui_state WHERE key = ?", (key,)).fetchone()
    if r:
        try:
            return json.loads(r["value"])
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def set_key(key, value):
    """Γενικό key-value store. Αποθηκεύει ένα JSON-able dict."""
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO ui_state (key, value) VALUES (?, ?)",
            (key, json.dumps(value, ensure_ascii=False)),
        )


# --- Κατηγορίες tags (folders/labels) ---

def set_category(video_id, category):
    """Ορίζει κατηγορία (label) για ΕΝΑ βίντεο. 1-προς-1: κάθε βίντεο ανήκει
    σε ΜΙΑ κατηγορία (ή καμία, αν category = '' / None). Αν η κατηγορία δεν
    υπάρχει, τη δημιουργεί αυτόματα στον πίνακα categories."""
    cat = (category or "").strip()
    with _conn() as c:
        if cat:
            r = c.execute("SELECT id FROM categories WHERE name = ?", (cat,)).fetchone()
            if not r:
                c.execute(
                    "INSERT INTO categories (name, created_at) VALUES (?, ?)",
                    (cat, now_iso()),
                )
        c.execute(
            "UPDATE videos SET user_category = ? WHERE video_id = ?",
            (cat or None, video_id),
        )


def create_category(name):
    """Δημιουργεί νέα κατηγορία (αν δεν υπάρχει). Επιστρέφει το id."""
    name = (name or "").strip()
    if not name:
        return None
    with _conn() as c:
        r = c.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
        if r:
            return r[0]
        cur = c.execute(
            "INSERT INTO categories (name, created_at) VALUES (?, ?)",
            (name, now_iso()),
        )
        return cur.lastrowid


def rename_category(old_name, new_name):
    """Μετονομάζει κατηγορία. Αλλάζει name στον πίνακα categories ΚΑΙ
    ενημερώνει όλα τα βίντεο που έχουν user_category == old_name."""
    old = (old_name or "").strip()
    new = (new_name or "").strip()
    if not old or not new:
        return
    with _conn() as c:
        c.execute("UPDATE categories SET name = ? WHERE name = ?", (new, old))
        c.execute("UPDATE videos SET user_category = ? WHERE user_category = ?", (new, old))


def delete_category(name):
    """Διαγράφει κατηγορία. Βίντεο που ανήκουν σε αυτήν γίνονται ακατηγοριοποίητα."""
    name = (name or "").strip()
    with _conn() as c:
        c.execute("DELETE FROM categories WHERE name = ?", (name,))
        c.execute("UPDATE videos SET user_category = NULL WHERE user_category = ?", (name,))


def all_categories():
    """Ταξινομημένη λίστα ονομάτων όλων των κατηγοριών."""
    with _conn() as c:
        return [r[0] for r in c.execute("SELECT name FROM categories ORDER BY name").fetchall()]


def set_channel_watch(channel_id, enabled, name=None):
    """Ορίζει αν ένα κανάλι παρακολουθείται από το RSS watchdog (toggle ανά κανάλι)."""
    channel_id = (channel_id or "").strip()
    if not channel_id:
        return
    with _conn() as c:
        if name:
            c.execute(
                "INSERT INTO channel_watch (channel_id, enabled, name) VALUES (?, ?, ?) "
                "ON CONFLICT(channel_id) DO UPDATE SET enabled = excluded.enabled, name = excluded.name",
                (channel_id, 1 if enabled else 0, name),
            )
        else:
            c.execute(
                "INSERT INTO channel_watch (channel_id, enabled) VALUES (?, ?) "
                "ON CONFLICT(channel_id) DO UPDATE SET enabled = excluded.enabled",
                (channel_id, 1 if enabled else 0),
            )


def watch_channels():
    """Λίστα channel_id που ο χρήστης παρακολουθεί (enabled=1)."""
    with _conn() as c:
        return [r[0] for r in c.execute(
            "SELECT channel_id FROM channel_watch WHERE enabled = 1"
        ).fetchall()]


def all_channel_watch():
    """Map channel_id -> enabled (για το dashboard, να ξέρει το frontend ποια ακολουθεί)."""
    with _conn() as c:
        return {r[0]: r[1] for r in c.execute(
            "SELECT channel_id, enabled FROM channel_watch"
        ).fetchall()}


def channel_watch_meta():
    """Map channel_id -> {enabled, name} (για εμφάνιση εισαγμένων καναλιών στη λίστα)."""
    with _conn() as c:
        out = {}
        for r in c.execute("SELECT channel_id, enabled, name FROM channel_watch").fetchall():
            out[r[0]] = {"enabled": r[1], "name": r[2] or ""}
        return out


def all_video_ids():
    """Set με όλα τα video_id στο ιστορικό (για το RSS watchdog: τι έχεις ήδη δει)."""
    with _conn() as c:
        return {r[0] for r in c.execute("SELECT video_id FROM videos").fetchall()}


def dismiss_video(video_id):
    """Απορρίπτει ένα βίντεο από το RSS (×) — δεν ξαναεμφανίζεται ποτέ στα «νέα»."""
    video_id = (video_id or "").strip()
    if not video_id:
        return
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO dismissed (video_id) VALUES (?)", (video_id,))


def dismissed_ids():
    """Set με όλα τα απορριμμένα video_id (×) — τα ξαναφιλτράρει ο RSS watchdog."""
    with _conn() as c:
        return {r[0] for r in c.execute("SELECT video_id FROM dismissed").fetchall()}


def add_recent_search(query):
    """Αποθηκεύει μια πρόσφατη αναζήτηση. Dedupe (case-insensitive) + κρατάει τις 50 πιο πρόσφατες."""
    query = (query or "").strip()
    if not query:
        return
    with _conn() as c:
        c.execute("DELETE FROM recent_searches WHERE lower(query) = lower(?)", (query,))
        c.execute("INSERT INTO recent_searches (query, searched_at) VALUES (?, ?)", (query, now_iso()))
        # κράτα μόνο τις 50 πιο πρόσφατες
        c.execute("""
            DELETE FROM recent_searches WHERE id NOT IN (
                SELECT id FROM recent_searches ORDER BY id DESC LIMIT 50
            )
        """)


def get_recent_searches():
    """Επιστρέφει τις 50 πιο πρόσφατες αναζητήσεις, από τη νεότερη στην παλαιότερη."""
    with _conn() as c:
        return [r[0] for r in c.execute(
            "SELECT query FROM recent_searches ORDER BY id DESC LIMIT 50"
        ).fetchall()]


def add_video_note(video_id, title, note, timestamp_sec):
    """Προσθέτει ένα timestamp note σε ένα βίντεο."""
    video_id = (video_id or "").strip()
    if not video_id:
        return None
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO video_notes (video_id, title, note, timestamp_sec, created_at) VALUES (?, ?, ?, ?, ?)",
            (video_id, (title or "").strip(), (note or "").strip(), int(timestamp_sec or 0), now_iso()),
        )
        return cur.lastrowid


def get_video_notes(video_id):
    """Επιστρέφει τα notes ενός βίντεο, ταξινομημένα κατά timestamp."""
    video_id = (video_id or "").strip()
    with _conn() as c:
        rows = c.execute(
            "SELECT id, title, note, timestamp_sec, created_at FROM video_notes WHERE video_id = ? ORDER BY timestamp_sec ASC, id ASC",
            (video_id,),
        ).fetchall()
        return [
            {"id": r["id"], "title": r["title"], "note": r["note"],
             "timestamp_sec": r["timestamp_sec"], "created_at": r["created_at"]}
            for r in rows
        ]


def delete_video_note(note_id):
    """Διαγράφει ένα note."""
    with _conn() as c:
        c.execute("DELETE FROM video_notes WHERE id = ?", (note_id,))


def all_video_notes():
    """Επιστρέφει {video_id: [notes]} για ΟΛΑ τα βίντεο — ΕΝΑ query (μπαίνει μέσα στο /api/dashboard)."""
    with _conn() as c:
        rows = c.execute(
            "SELECT video_id, id, title, note, timestamp_sec FROM video_notes ORDER BY timestamp_sec ASC, id ASC"
        ).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["video_id"], []).append(
            {"id": r["id"], "title": r["title"], "note": r["note"], "timestamp_sec": r["timestamp_sec"]}
        )
    return out


def cache_channel_videos(channel_id, videos):
    """Αποθηκεύει (ή ενημερώνει) τα βίντεο ενός καναλιού στη cache, με τη σειρά τους.

    videos: λίστα από {video_id, title} με τη σειρά «νεότερα → παλιότερα».
    """
    channel_id = (channel_id or "").strip()
    if not channel_id or not videos:
        return
    now = now_iso()
    with _conn() as c:
        for pos, v in enumerate(videos):
            c.execute(
                """
                INSERT OR REPLACE INTO channel_videos_cache
                    (channel_id, video_id, title, position, cached_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (channel_id, v.get("video_id"), v.get("title") or "", pos, now),
            )


def get_cached_channel_videos(channel_id, offset=0, limit=10):
    """Επιστρέφει cached βίντεα ενός καναλιού, ταξινομημένα νεότερα→παλιότερα, με pagination."""
    with _conn() as c:
        rows = c.execute(
            """
            SELECT video_id, title FROM channel_videos_cache
            WHERE channel_id = ?
            ORDER BY position ASC
            LIMIT ? OFFSET ?
            """,
            (channel_id, limit, offset),
        ).fetchall()
        return [{"video_id": r["video_id"], "title": r["title"]} for r in rows]


# --- 🔍 Cache αναζήτησης ---

def save_search_results(query, mode, entries, start=0, replace_all=False):
    """Αποθηκεύει σελίδα αποτελεσμάτων (με τη σειρά) για ένα query+mode.

    start       → σε ποια θέση ξεκινά (π.χ. offset=24 → θέση 24), ωστόσο η cache
                  κρατά ΜΙΑ ΣΥΝΕΧΗ ακολουθία από το 0 — δεν σβήνει τις προηγούμενες σελίδες.
    replace_all → True μόνο όταν ξεκινάμε ΝΕΑ αναζήτηση (καθαρίζει τα παλιά).
    """
    query = (query or "").strip()
    if not query or not entries:
        return
    now = now_iso()
    with _conn() as c:
        if replace_all:
            # Νέα αναζήτηση: σβήσε τα παλιά αποτελέσματα (ΚΡΑΤΑ το «εξαντλήθηκε» = position -1).
            c.execute("DELETE FROM search_cache WHERE query = ? AND mode = ? AND position >= 0", (query, mode))
        c.executemany(
            """INSERT OR REPLACE INTO search_cache
               (query, mode, position, video_id, title, channel, channel_id, duration, views, cached_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            # 🔑 Και τα βίντεο ΚΑΙ τα κανάλια: κλειδί = video_id ή channel_id (τα κανάλια δεν έχουν video_id).
            # Τα κανάλια έχουν «name» (όχι title/channel) — γι' αυτό εδώ το name μπαίνει πρώτο.
            [(query, mode, start + i, e.get("video_id") or e.get("channel_id"),
              e.get("title") or e.get("name") or "",
              e.get("channel") or e.get("name") or e.get("title") or "", e.get("channel_id") or "",
              int(e.get("duration") or 0), int(e.get("views") or 0), now)
             for i, e in enumerate(entries) if (e.get("video_id") or e.get("channel_id"))],
        )


def get_search_results(query, mode, offset=0, limit=100):
    """Διαβάζει σελίδα αποτελεσμάτων από τη cache — ΜΗΔΕΝ δίκτυο."""
    query = (query or "").strip()
    if not query:
        return []
    with _conn() as c:
        rows = c.execute(
            """SELECT video_id, title, channel, channel_id, duration, views FROM search_cache
               WHERE query = ? AND mode = ? ORDER BY position ASC LIMIT ? OFFSET ?""",
            (query, mode, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def search_exhausted(query, mode):
    """🔚 True αν ξέρουμε ότι το YouTube δεν έχει άλλα για αυτό το query+mode.
    Σημειώνεται με ειδική γραμμή position = -1."""
    query = (query or "").strip()
    if not query:
        return False
    with _conn() as c:
        r = c.execute("SELECT 1 FROM search_cache WHERE query = ? AND mode = ? AND position = -1 LIMIT 1",
                      (query, mode)).fetchone()
        return bool(r)


def mark_search_exhausted(query, mode):
    """Σημειώνει ότι το YouTube δεν έδωσε άλλα αποτελέσματα (τέλος)."""
    query = (query or "").strip()
    if not query:
        return
    with _conn() as c:
        c.execute("""INSERT OR REPLACE INTO search_cache
                     (query, mode, position, video_id, title, channel, channel_id, duration, views, cached_at)
                     VALUES (?, ?, -1, NULL, '', '', '', 0, 0, ?)""", (query, mode, now_iso()))


def count_search_results(query, mode):
    """Πόσα αποτελέσματα ξέρουμε για αυτό το query+mode."""
    query = (query or "").strip()
    if not query:
        return 0
    with _conn() as c:
        r = c.execute("SELECT COUNT(*) AS n FROM search_cache WHERE query = ? AND mode = ?",
                      (query, mode)).fetchone()
        return r["n"] if r else 0


def first_cached_channel_video(channel_id):
    """Το ΝΕΟΤΕΡΟ βίντεο που ξέρουμε από αυτό το κανάλι (θέση 0). None αν δεν ξέρουμε.
    Χρησιμοποιείται για το γρήγορο «δεν υπάρχει τίποτα νέο» — χωρίς δεύτερο δικτυακό αίτημα."""
    with _conn() as c:
        r = c.execute(
            "SELECT video_id FROM channel_videos_cache WHERE channel_id = ? ORDER BY position ASC LIMIT 1",
            (channel_id,),
        ).fetchone()
        return r["video_id"] if r else None


def count_cached_channel_videos(channel_id):
    with _conn() as c:
        r = c.execute(
            "SELECT COUNT(*) AS n FROM channel_videos_cache WHERE channel_id = ?",
            (channel_id,),
        ).fetchone()
        return r["n"] if r else 0


# --- Export / Import (πλήρης κλώνος της βάσης για backup ή μεταφορά σε άλλο PC) ---

# Οι πίνακες σε σειρά εισαγωγής (οι "απλοί" πρώτα, τα βίντεο τελευταία ώστε να μην
# σπάνε τα FOREIGN KEY, κι όλα τα υπόλοιπα μετά). watch_events έχει FK σε videos,
# άρα γράφεται ΜΕΤΑ τα videos.
EXPORT_TABLES = [
    "categories",
    "tag_stats",
    "channel_tags",
    "channel_watch",
    "ui_state",
    "dismissed",
    "videos",
    "watch_events",
]


def _safe_table(table):
    """Επιστρέφει το table name μόνο αν είναι σε whitelist (αποτρέπει SQL injection μέσω
    κακόβουλου export αρχείου). Αλλιώς κάνει raise."""
    if table not in EXPORT_TABLES:
        raise ValueError(f"Μη επιτρεπτός πίνακας: {table}")
    return table


def _safe_cols(table, cols):
    """Επικυρώνει ότι ΟΛΑ τα column names ανήκουν πραγματικά στον πίνακα (whitelist βάσει
    PRAGMA table_info). Αποτρέπει SQL injection μέσω κακόβουλων ονομάτων στηλών σε export."""
    cols = [str(c) for c in (cols or [])]
    with _conn() as c:
        valid = {r[1] for r in c.execute(f"PRAGMA table_info({_safe_table(table)})").fetchall()}
    for col in cols:
        if col not in valid:
            raise ValueError(f"Μη επιτρεπτή στήλη για {table}: {col}")
    return cols


def export_all():
    """Σειριοποιεί ΟΛΟΥΣ τους πίνακες σε ένα dict (JSON-ready)."""
    out = {"version": 1, "tables": {}}
    with _conn() as c:
        for table in EXPORT_TABLES:
            t = _safe_table(table)
            rows = c.execute(f"SELECT * FROM {t}").fetchall()
            cols = [d[0] for d in c.execute(f"SELECT * FROM {t}").description]
            out["tables"][table] = {
                "columns": cols,
                "rows": [list(r) for r in rows],
            }
    return out


def import_all(data, mode="replace"):
    """Γράφει τα δεδομένα ενός export πίσω στη βάση.

    mode = "replace" → σβήνει τα πάντα και βάζει το αρχείο (καθαρός κλώνος).
    mode = "merge"   → προσθέτει δίπλα στα υπάρχοντα ΧΩΡΙΣ διπλότυπα.
    """
    tables = data.get("tables") or {}
    if data.get("version") != 1:
        raise ValueError(f"Μη υποστηριζόμενη έκδοση export: {data.get('version')}")

    def _spec(table):
        s = tables.get(table) or {}
        cols = s.get("columns") or []
        rows = s.get("rows") or []
        return cols, rows

    with _conn() as c:
        if mode == "replace":
            # Καθαρός κλώνος: σβήσε κάθε πίνακα, βάλε τα πάντα με τη σωστή σειρά (FK).
            for table in EXPORT_TABLES:
                cols, rows = _spec(table)
                if not cols:
                    continue
                cols = _safe_cols(table, cols)
                t = _safe_table(table)
                col_list = ", ".join(cols)
                ph = ", ".join("?" for _ in cols)
                c.execute(f"DELETE FROM {t}")
                c.executemany(
                    f"INSERT OR IGNORE INTO {t} ({col_list}) VALUES ({ph})",
                    [tuple(r) for r in rows],
                )
            return

        # --- MERGE (χωρίς διπλότυπα) ---
        # 1) categories: UNIQUE(name) → κράτα τοπικά ονόματα.
        cols, rows = _spec("categories")
        if cols:
            cols = _safe_cols("categories", cols)
            ph = ", ".join("?" for _ in cols)
            c.executemany(
                f"INSERT OR IGNORE INTO categories ({', '.join(cols)}) VALUES ({ph})",
                [tuple(r) for r in rows],
            )

        # 2) videos: PRIMARY KEY video_id → μην ξαναγράψεις υπάρχοντα.
        cols, rows = _spec("videos")
        if cols:
            cols = _safe_cols("videos", cols)
            ph = ", ".join("?" for _ in cols)
            c.executemany(
                f"INSERT OR IGNORE INTO videos ({', '.join(cols)}) VALUES ({ph})",
                [tuple(r) for r in rows],
            )

        # 3) watch_events: βάλε events ΜΟΝΟ για βίντεο που δεν υπήρχαν ήδη τοπικά.
        #    (αλλιώς θα διπλασιάζαμε προβολές σε βίντεο που ήδη έχεις).
        local_ids = {r[0] for r in c.execute("SELECT video_id FROM videos").fetchall()}
        cols, rows = _spec("watch_events")
        if cols:
            cols = _safe_cols("watch_events", cols)
            col_list = ", ".join(cols)
            ph = ", ".join("?" for _ in cols)
            # βρες τη θέση του video_id στις στήλες
            vid_idx = cols.index("video_id") if "video_id" in cols else None
            for r in rows:
                if vid_idx is not None and r[vid_idx] in local_ids:
                    continue  # το βίντεο υπήρχε ήδη → άσε τα τοπικά events του
                c.execute(f"INSERT OR IGNORE INTO watch_events ({col_list}) VALUES ({ph})", tuple(r))

        # 4) σύνολα (PK = το ίδιο το κλειδί): INSERT OR IGNORE κρατάει το τοπικό.
        for table in ("dismissed", "channel_watch", "channel_tags"):
            cols, rows = _spec(table)
            if not cols:
                continue
            cols = _safe_cols(table, cols)
            ph = ", ".join("?" for _ in cols)
            c.executemany(
                f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) VALUES ({ph})",
                [tuple(r) for r in rows],
            )

        # 5) tag_stats: πρόσθεσε τα use_count στα υπάρχοντα (να μην ξαναμηδενίζει).
        cols, rows = _spec("tag_stats")
        if cols:
            cols = _safe_cols("tag_stats", cols)
            tag_idx = cols.index("tag") if "tag" in cols else None
            cnt_idx = cols.index("use_count") if "use_count" in cols else None
            for r in rows:
                tag = r[tag_idx] if tag_idx is not None else None
                if tag is None:
                    continue
                exists = c.execute("SELECT use_count FROM tag_stats WHERE tag = ?", (tag,)).fetchone()
                if exists and cnt_idx is not None:
                    c.execute("UPDATE tag_stats SET use_count = use_count + ? WHERE tag = ?", (r[cnt_idx] or 0, tag))
                else:
                    c.execute(
                        f"INSERT OR IGNORE INTO tag_stats ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                        tuple(r),
                    )

        # 6) ui_state: ΚΡΑΤΩ το τοπικό (η σειρά/σύμπτυξη του χρήστη δεν πρέπει να αλλάξει σε merge).
        #    (δεν κάνουμε τίποτα)
