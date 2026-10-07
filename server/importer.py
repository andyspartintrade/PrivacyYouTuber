"""Εισαγωγή υπάρχοντος ιστορικού YouTube από ένα Google Takeout export.

Χρήση:
    python cli.py import "C:/path/to/Takeout"

Βρίσκει αυτόματα το watch-history.json (όσο βαθιά κι αν είναι μέσα στον φάκελο)
και το subscriptions.csv για ενημέρωση.

Privacy: το Takeout είναι η επίσημη, μία φορά, εξαγωγή των δεδομένων ΣΟΥ.
Μετά την εισαγωγή, τα δεδομένα ζουν μόνο τοπικά στη βάση μας.
"""

import csv
import html
import json
import os
import re

from . import db

# Ένα YouTube video id είναι 11 χαρακτήρες (γράμματα/ψηφία/-/_).
VIDEO_RE = re.compile(r"[?&]v=([A-Za-z0-9_-]{11})")

# Το πρόθεμα στον τίτλο εξαρτάται από τη γλώσσα του λογαριασμού.
_TITLE_PREFIX = re.compile(
    r"^(Watched|Παρακολούθηση|Παρακολουθήθηκε|Παρακολούθησα)\s+",
    flags=re.IGNORECASE,
)


def _clean_title(raw):
    t = html.unescape(re.sub(r"<[^>]+>", "", raw or ""))
    return _TITLE_PREFIX.sub("", t).strip()


def parse_watch_history(path):
    """Επιστρέφει λίστα {video_id, title, channel, watched_at} από το JSON."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    entries = []
    for item in data:
        url = item.get("titleUrl") or ""
        m = VIDEO_RE.search(url)
        if not m:
            continue  # δεν είναι βίντεο (αναζήτηση, διαφήμιση, κανάλι...)
        subs = item.get("subtitles") or []
        channel = subs[0].get("name", "") if subs else ""
        entries.append(
            {
                "video_id": m.group(1),
                "title": _clean_title(item.get("title")),
                "channel": channel,
                "watched_at": item.get("time"),
            }
        )
    return entries


def find_takeout_file(export_dir, filename):
    direct = os.path.join(export_dir, filename)
    if os.path.isfile(direct):
        return direct
    for root, _dirs, files in os.walk(export_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None


def parse_subscriptions_csv(path):
    """Διαβάζει το subscriptions.csv (Google Takeout) και επιστρέφει λίστα channel_id."""
    return [r["id"] for r in parse_subscriptions_csv_with_names(path)]


def parse_subscriptions_csv_with_names(path):
    """Διαβάζει το subscriptions.csv και επιστρέφει λίστα {id, name}.

    Δουλεύει για ΟΠΟΙΑΔΗΠΟΤΕ γλώσσα (αγγλικά/ελληνικά headers) γιατί ανιχνεύει
    το channel id από το μοτίβο UC... σε ΟΠΟΙΑΔΗΠΟΤΕ στήλη. Το όνομα το παίρνει
    από την ΤΕΛΕΥΤΑΙΑ στήλη κάθε γραμμής (Τίτλος καναλιού).
    """
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return []

    cid_re = re.compile(r"UC[A-Za-z0-9_-]{22}")
    url_re = re.compile(r"/channel/(UC[A-Za-z0-9_-]{22})")

    out = []
    seen = set()
    for row in rows[1:]:  # skip επικεφαλίδας
        if not row:
            continue
        cid = None
        name = ""
        # το όνομα = τελευταία μη-κενή στήλη που ΔΕΝ είναι id/url
        for cell in row:
            cell = (cell or "").strip()
            if not cell:
                continue
            m = cid_re.fullmatch(cell) or url_re.search(cell)
            if m:
                cid = (m.group(0) if cid_re.fullmatch(cell) else m.group(1))
            else:
                name = cell  # κρατά το τελευταίο "τίτλο" κείμενο
        if cid and cid not in seen:
            seen.add(cid)
            out.append({"id": cid, "name": name or cid})
    return out


def run(export_dir):
    db.init()

    history_path = find_takeout_file(export_dir, "watch-history.json")
    if not history_path:
        print("❌ Δεν βρήκα watch-history.json μέσα στο:")
        print(f"   {export_dir}")
        print("   Σιγουρέψου ότι έκανες export σε μορφή JSON από το takeout.google.com")
        print("   (Multiple formats → History → JSON).")
        return

    entries = parse_watch_history(history_path)
    before = db.count_videos()
    for e in entries:
        db.import_watch(e["video_id"], e["title"], e["channel"], e["watched_at"])
    after = db.count_videos()

    print(f"✅ Διάβασα {len(entries)} εγγραφές ιστορικού.")
    print(f"   Μοναδικά βίντεο στη βάση: {before} → {after}")
    print("   (τα διπλότυπα συγχωνεύτηκαν και αύξησαν το watch_count)")

    subs_path = find_takeout_file(export_dir, "subscriptions.csv")
    if subs_path:
        with open(subs_path, encoding="utf-8") as f:
            n_subs = sum(1 for _ in csv.reader(f)) - 1  # -1 για την επικεφαλίδα
        print(f"   📌 Βρήκα και {n_subs} συνδρομές (subscriptions.csv).")
        print("      Phase 2: προτάσεις απευθείας από τα κανάλια που ακολουθείς.")
