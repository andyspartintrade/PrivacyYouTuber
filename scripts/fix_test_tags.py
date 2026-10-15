"""Bug 2: καθαρισμός test tags (-PENTAPLEX, --PENTAPLEX) από τη βάση.
Backup πρώτα. Ασφαλές: UPDATE μόνο στα προσβεβλημένα.
"""
import sqlite3, os, shutil, datetime, json

db = os.path.expandvars(r"%LOCALAPPDATA%\PrivacyYouTuber\privacy_yt.db")
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(db, f"{db}.backup-{stamp}")
print(f"[OK] backup: privacy_yt.db.backup-{stamp}")

con = sqlite3.connect(db)
con.row_factory = sqlite3.Row

# ── ΕΛΕΓΧΟΣ ΤΩΝ ΠΡΟΣΒΕΒΛΗΜΕΝΩΝ ──
print("\n=== ΠΡΙΝ ===")
print("channel_tags:")
for x in con.execute("SELECT channel_id, tags FROM channel_tags WHERE tags LIKE '%PENTA%'"):
    print(f"  {x['channel_id']} -> {x['tags']}")
print("my_tags:")
for x in con.execute("SELECT video_id, my_tags FROM videos WHERE my_tags LIKE '%PENTA%'"):
    print(f"  {x['video_id']} -> {x['my_tags']}")

# ── ΚΑΘΑΡΙΣΜΟΣ ──
# 1. channel_tags: αφαίρεσε τα tags που ξεκινούν με "-" (test εξαιρέσεις)
fixed_ct = 0
for x in con.execute("SELECT channel_id, tags FROM channel_tags"):
    try:
        tags = json.loads(x["tags"] or "[]")
    except Exception:
        continue
    clean = [t for t in tags if not t.startswith("-")]
    if clean != tags:
        con.execute("UPDATE channel_tags SET tags = ? WHERE channel_id = ?",
                    (json.dumps(clean, ensure_ascii=False), x["channel_id"]))
        fixed_ct += 1
        print(f"  [fix] channel {x['channel_id']}: {tags} -> {clean}")

# 2. videos.my_tags: αφαίρεσε τα tags που ξεκινούν με "--" (διπλά) και τα "-PENTAPLEX"
fixed_v = 0
for x in con.execute("SELECT video_id, my_tags FROM videos WHERE my_tags IS NOT NULL AND my_tags != '[]'"):
    try:
        tags = json.loads(x["my_tags"] or "[]")
    except Exception:
        continue
    # κράτα τα έγκυρα "-tag" (εξαιρέσεις), διώξε τα "--tag" και τα "-PENTAPLEX" (test)
    clean = [t for t in tags if not t.startswith("--") and t != "-PENTAPLEX"]
    if clean != tags:
        con.execute("UPDATE videos SET my_tags = ? WHERE video_id = ?",
                    (json.dumps(clean, ensure_ascii=False), x["video_id"]))
        fixed_v += 1
        print(f"  [fix] video {x['video_id']}: {tags} -> {clean}")

con.commit()
print(f"\n[OK] channel_tags: {fixed_ct} | videos: {fixed_v}")

# ── ΜΕΤΑ ──
print("\n=== ΜΕΤΑ ===")
print("PENTA που έμειναν:")
n = con.execute("SELECT COUNT(*) FROM channel_tags WHERE tags LIKE '%PENTA%'").fetchone()[0]
n += con.execute("SELECT COUNT(*) FROM videos WHERE my_tags LIKE '%PENTA%'").fetchone()[0]
print(f"  {n} (πρέπει 0)")
print("\nΌλα τα tags τώρα:")
seen = set()
for x in con.execute("SELECT tags FROM channel_tags WHERE tags != '[]'"):
    for t in json.loads(x["tags"] or "[]"):
        seen.add(t)
for x in con.execute("SELECT my_tags FROM videos WHERE my_tags IS NOT NULL AND my_tags != '[]'"):
    for t in json.loads(x["my_tags"] or "[]"):
        seen.add(t)
print("  ", sorted(seen))
