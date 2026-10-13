"""FIX: το fillChannelGrid πρεπει να φιλτραρει με τα ΕΝΕΡΓΑ tags/rating
(γι' αυτο εμφανιζοταν βιντεο που δεν ειχαν πια το tag μεσα στο καναλι).

Επισης: το cache (dataset.filled) πρεπει να ακυρωνεται οταν αλλαζει το φιλτρο.
- Αποθηκευουμε το «state» του φιλτρου στο dataset.filterKey.
- Αν αλλαξει -> ξαναγεμιζουμε.
"""
p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

old = '''function fillChannelGrid(group) {
  if (!group) return;
  const g = group.querySelector(".v-card-grid");
  if (!g || g.dataset.filled) return;
  const k = group.dataset.key;
  const vids = allVideos.filter(v => (v.channel_id || v.channel || "__unknown__") === k);
  const sorted = vids.slice().sort((a, b) =>
    (b.rank || 0) - (a.rank || 0) || (b.watch_count || 0) - (a.watch_count || 0));
  g.innerHTML = sorted.map(v => cardHtml(v, "channel")).join("");
  g.dataset.filled = "1";
  applyI18n(g);
  setupDrag();
}'''

new = '''function fillChannelGrid(group) {
  if (!group) return;
  const g = group.querySelector(".v-card-grid");
  if (!g) return;
  // 🔑 Το cache ισχύει ΜΟΝΟ για το ΙΔΙΟ φίλτρο. Άλλαξε το φίλτρο → ξαναγέμισε.
  const filterKey = [...selectedTags].sort().join("|") + "#" + searchRating
                    + "#" + (document.getElementById("search-input").value || "").trim();
  if (g.dataset.filled && g.dataset.filterKey === filterKey) return;
  const k = group.dataset.key;
  let vids = allVideos.filter(v => (v.channel_id || v.channel || "__unknown__") === k);
  // 🏷️ Με ΕΝΕΡΓΟ φίλτρο tag/rating: ΔΕΙΞΕ ΜΟΝΟ όσα ταιριάζουν (σέβεται αρνήσεις).
  if (selectedTags.size > 0 || searchRating > 0) {
    vids = vids.filter(v => {
      if (searchRating > 0 && (v.rating || 0) === searchRating) return true;
      for (const t of selectedTags) if (videoTags(v).includes(t)) return true;
      return false;
    });
  }
  const sorted = vids.slice().sort((a, b) =>
    (b.rank || 0) - (a.rank || 0) || (b.watch_count || 0) - (a.watch_count || 0));
  g.innerHTML = sorted.map(v => cardHtml(v, "channel")).join("");
  g.dataset.filled = "1";
  g.dataset.filterKey = filterKey;
  applyI18n(g);
  setupDrag();
}

/* 🔄 Ακυρώνει το cache ΟΛΩΝ των grids — κλήσ' το όταν αλλάζει φίλτρο/tags. */
function invalidateChannelGrids() {
  document.querySelectorAll(".channel-group .v-card-grid").forEach(g => {
    delete g.dataset.filled;
    delete g.dataset.filterKey;
  });
}'''

if old in s:
    s = s.replace(old, new); n += 1; print("[OK] fillChannelGrid: φιλτραρει με tags + φρεσκο cache")
else:
    print("[FAIL] fillChannelGrid")

open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
