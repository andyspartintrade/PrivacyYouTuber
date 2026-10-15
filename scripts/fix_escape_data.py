"""Bug 1: διόρθωση του literal \\u0026 στα ΔΕΔΟΜΕΝΑ (videos.channel).
Ασφαλές: UPDATE σε 1 στήλη, μόνο για την προσβεβλημένη εγγραφή. Backup πρώτα.
"""
import sqlite3, os, shutil, datetime

db = os.path.expandvars(r"%LOCALAPPDATA%\PrivacyYouTuber\privacy_yt.db")

# ── BACKUP ──
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(db, f"{db}.backup-{stamp}")
print(f"[OK] backup: privacy_yt.db.backup-{stamp}")

con = sqlite3.connect(db)

print("\n=== ΠΡΙΝ ===")
for r in con.execute("SELECT video_id, channel FROM videos WHERE channel LIKE '%u0026%'"):
    print(f"  {r[0]} | {r[1]}")

# ── ΔΙΟΡΘΩΣΗ ──
cur = con.execute("""
    UPDATE videos
       SET channel = REPLACE(REPLACE(channel, '\\u0026', '&'),
                             '\\u0026', '&')
     WHERE channel LIKE '%u0026%'
""")
con.commit()
print(f"\n[OK] Γράφτηκαν: {cur.rowcount} γραμμές")

print("\n=== ΜΕΤΑ ===")
for r in con.execute("SELECT video_id, channel FROM videos WHERE channel LIKE '%Crystal%'"):
    print(f"  {r[0]} | {r[1]!r}")
