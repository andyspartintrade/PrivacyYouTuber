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
        # channel_watch: πρόσθεσε στήλη name (για εισαγμένα subscriptions).
        wcols = [r[1] for r in c.execute("PRAGMA table_info(channel_watch)").fetchall()]
        if "name" not in wcols:
            c.execute("ALTER TABLE channel_watch ADD COLUMN name TEXT")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def record_watch(event):
    """Καταγράφει (ή ενημερώνει) ένα βίντεο από το payload του extension."""
    vid = event.get("video_id")
    if not vid:
        return
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
                    channel          = COALESCE(?, channel),
                    channel_id       = COALESCE(?, channel_id),
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


def set_pin_channel(channel_id, state):
    """Καρφιτσώνει/ξεκαρφιτσώνει ΟΛΑ τα βίντεα ενός καναλιού (Keep-στυλ: pinned 1 / unpinned 0)."""
    with _conn() as c:
        vids = c.execute(
            "SELECT video_id FROM videos WHERE channel_id = ?", (channel_id,)
        ).fetchall()
        if not vids:
            return 0
        new = 1 if state else 0
        for r in vids:
            c.execute("UPDATE videos SET pinned = ? WHERE video_id = ?", (new, r["video_id"]))
        return new


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
    return {
        "videos": videos,
        "events": events,
        "top_channel": top["channel"] if top else None,
        "top_channel_count": top["n"] if top else 0,
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
    """Αποθηκεύει αν ένα βίντεο επιτρέπει embed (1=ναι, 0=όχι)."""
    with _conn() as c:
        c.execute(
            "UPDATE videos SET is_embeddable = ? WHERE video_id = ?",
            (1 if ok else 0, video_id),
        )


def get_embeddable(video_id):
    """Επιστρέφει True/False/None (άγνωστο) για το embed status."""
    with _conn() as c:
        r = c.execute(
            "SELECT is_embeddable FROM videos WHERE video_id = ?", (video_id,)
        ).fetchone()
        if not r or r[0] is None:
            return None
        return bool(r[0])


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
    """Αποθηκεύει μια πρόσφατη αναζήτηση. Dedupe (case-insensitive) + κρατάει τις 10 πιο πρόσφατες."""
    query = (query or "").strip()
    if not query:
        return
    with _conn() as c:
        c.execute("DELETE FROM recent_searches WHERE lower(query) = lower(?)", (query,))
        c.execute("INSERT INTO recent_searches (query, searched_at) VALUES (?, ?)", (query, now_iso()))
        # κράτα μόνο τις 10 πιο πρόσφατες
        c.execute("""
            DELETE FROM recent_searches WHERE id NOT IN (
                SELECT id FROM recent_searches ORDER BY id DESC LIMIT 10
            )
        """)


def get_recent_searches():
    """Επιστρέφει τις 10 πιο πρόσφατες αναζητήσεις, από τη νεότερη στην παλαιότερη."""
    with _conn() as c:
        return [r[0] for r in c.execute(
            "SELECT query FROM recent_searches ORDER BY id DESC LIMIT 10"
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


def video_notes_for_videos(video_ids):
    """Επιστρέφει {video_id: [notes]} για μια λίστα βίντεο (για τα cards)."""
    if not video_ids:
        return {}
    with _conn() as c:
        qmarks = ",".join("?" for _ in video_ids)
        rows = c.execute(
            f"SELECT video_id, id, title, note, timestamp_sec FROM video_notes WHERE video_id IN ({qmarks}) ORDER BY timestamp_sec ASC, id ASC",
            tuple(video_ids),
        ).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["video_id"], []).append(
            {"id": r["id"], "title": r["title"], "note": r["note"], "timestamp_sec": r["timestamp_sec"]}
        )
    return out


# --- Cache ιστορικού καναλιού (preload/pagination) ---

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


def export_all():
    """Σειριοποιεί ΟΛΟΥΣ τους πίνακες σε ένα dict (JSON-ready)."""
    out = {"version": 1, "tables": {}}
    with _conn() as c:
        for table in EXPORT_TABLES:
            rows = c.execute(f"SELECT * FROM {table}").fetchall()
            cols = [d[0] for d in c.execute(f"SELECT * FROM {table}").description]
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
                col_list = ", ".join(cols)
                ph = ", ".join("?" for _ in cols)
                c.execute(f"DELETE FROM {table}")
                c.executemany(
                    f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({ph})",
                    [tuple(r) for r in rows],
                )
            return

        # --- MERGE (χωρίς διπλότυπα) ---
        # 1) categories: UNIQUE(name) → κράτα τοπικά ονόματα.
        cols, rows = _spec("categories")
        if cols:
            ph = ", ".join("?" for _ in cols)
            c.executemany(
                f"INSERT OR IGNORE INTO categories ({', '.join(cols)}) VALUES ({ph})",
                [tuple(r) for r in rows],
            )

        # 2) videos: PRIMARY KEY video_id → μην ξαναγράψεις υπάρχοντα.
        cols, rows = _spec("videos")
        if cols:
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
            ph = ", ".join("?" for _ in cols)
            c.executemany(
                f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) VALUES ({ph})",
                [tuple(r) for r in rows],
            )

        # 5) tag_stats: πρόσθεσε τα use_count στα υπάρχοντα (να μην ξαναμηδενίζει).
        cols, rows = _spec("tag_stats")
        if cols:
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
