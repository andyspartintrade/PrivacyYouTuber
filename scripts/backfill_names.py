"""Backfill: γεμίζει το channel_watch.name από το videos table (ΜΟΝΟ όπου είναι NULL).
Ασφαλές: UPDATE σε 1 στήλη, τα βίντεο ΔΕΝ αγγίζονται. Backup έχει ήδη γίνει."""
import sqlite3, os, sys

db = os.path.expandvars(r"%LOCALAPPDATA%\PrivacyYouTuber\privacy_yt.db")
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row

print("=== ΠΡΙΝ ===")
before = con.execute("SELECT COUNT(*) c FROM channel_watch WHERE name IS NULL").fetchone()["c"]
print(f"  name IS NULL: {before}")

# Δείξε τι θα αλλάξει (dry-run)
print("\n=== ΘΑ ΑΛΛΑΞΟΥΝ ===")
to_fix = []
for r in con.execute("SELECT channel_id, name FROM channel_watch WHERE name IS NULL"):
    v = con.execute(
        "SELECT channel FROM videos WHERE channel_id=? AND channel IS NOT NULL AND channel!='' LIMIT 1",
        (r["channel_id"],)).fetchone()
    if v:
        to_fix.append((v["channel"], r["channel_id"]))
for name, cid in to_fix[:10]:
    print(f"  {cid} → {name}")
if len(to_fix) > 10:
    print(f"  ... και άλλα {len(to_fix)-10}")

# UPDATE
cur = con.execute("""
    UPDATE channel_watch
       SET name = (SELECT v.channel FROM videos v
                    WHERE v.channel_id = channel_watch.channel_id
                      AND v.channel IS NOT NULL AND v.channel != ''
                    LIMIT 1)
     WHERE name IS NULL
       AND EXISTS (SELECT 1 FROM videos v2
                    WHERE v2.channel_id = channel_watch.channel_id
                      AND v2.channel IS NOT NULL AND v2.channel != '')
""")
con.commit()

print("\n=== ΜΕΤΑ ===")
after = con.execute("SELECT COUNT(*) c FROM channel_watch WHERE name IS NULL").fetchone()["c"]
print(f"  name IS NULL: {after}")
print(f"  Γράφτηκαν: {cur.rowcount}")
print(f"\n{'✅ ΕΠΙΤΥΧΙΑ' if after < before else '⚠️ ΚΑΜΙΑ ΑΛΛΑΓΗ'}")
