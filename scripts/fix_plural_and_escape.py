"""Bug 3: πληθυντικός (1 video vs N videos) — και στα 2 UI σημεία.
Bug 1: διάγνωση του \\u0026 (escape σε δεδομένα).
"""
import re, json

p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

# ─── Πληθυντικός: helper ───
helper = '''
/* 🔢 Πληθυντικός: 1 video / N videos (+ ΕΛ: 1 βίντεο / N βίντεο — ίδιο και στα δύο). */
function vidsWord(n) {
  // Αγγλικά: 1 → " video", αλλιώς " videos". Ελληνικά: αμετάβλητο (" βίντεο").
  if ((window.i18n && window.i18n.getLang && window.i18n.getLang() === "el") || n !== 1) {
    return t("misc.videosWord");
  }
  return t("misc.videoWord");
}
'''
# βάλε τον helper πριν το esc()
if "function vidsWord(" not in s:
    m = re.search(r"\nfunction esc\(s\) \{", s)
    if m:
        s = s[:m.start()] + "\n" + helper + s[m.start():]
        n += 1
        print("[OK] helper vidsWord()")

# ─── Αντικατέστησε τα 4 σημεία ───
subs = [
    ("""`<span class="sep">·</span><b>${s.videos ?? 0}</b>${t('misc.videosWord')}`""",
     """`<span class="sep">·</span><b>${s.videos ?? 0}</b>${vidsWord(s.videos ?? 0)}`"""),
    ("""fc.textContent = `· ${count}${t('misc.videosWord')}`;""",
     """fc.textContent = `· ${count}${vidsWord(count)}`;"""),
    ("""<span class="muted">· ${vids.length}${t('misc.videosWord')}</span>""",
     """<span class="muted">· ${vids.length}${vidsWord(vids.length)}</span>"""),
    ("""<span class="cat-count">· ${vids.length}${t('misc.videosWord')}</span>""",
     """<span class="cat-count">· ${vids.length}${vidsWord(vids.length)}</span>"""),
]
for old, new in subs:
    if old in s:
        s = s.replace(old, new)
        n += 1
        print(f"[OK] {old[:50]}...")

open(p, "w", encoding="utf-8").write(s)

# ─── i18n key: videoWord ───
jp = "web/i18n.json"
d = json.load(open(jp, encoding="utf-8"))
if "misc.videoWord" not in d:
    d["misc.videoWord"] = {"en": " video", "el": " βίντεο"}
    json.dump(d, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    n += 1
    print("[OK] misc.videoWord key")

print(f"\nchanges: {n}")
