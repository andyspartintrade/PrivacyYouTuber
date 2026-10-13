"""FIX (γενικο): το «imported» branch ΔΕΝ τρεχει οταν υπαρχει ενεργο φιλτρο.
Επισης: fallback ονοματος απο τα βιντεο (οχι raw channel_id)."""
p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

old = '''  // 📡 Εισαγμένα κανάλια (συνδρομές, χωρίς βίντεο) — στο κάτω μέρος, πορτοκαλί banner, καμπανάκι on/off.
  const existingKeys = new Set(groups.keys());
  for (const cid of Object.keys(WATCHED_META)) {
    if (existingKeys.has(cid)) continue;  // ήδη εμφανίζεται (έχει βίντεο)
    const meta = WATCHED_META[cid] || {};
    const name = meta.name || cid;'''

new = '''  // 📡 Εισαγμένα κανάλια (συνδρομές, χωρίς βίντεο) — στο κάτω μέρος, κίτρινο banner.
  // 🚫 ΜΟΝΟ όταν ΔΕΝ υπάρχει φίλτρο: με φίλτρο δείχνουμε ΜΟΝΟ ό,τι ταιριάζει.
  //    (Αλλιώς, με tag filter, δεκάδες κανάλια χωρίς ταιριαστά βίντεο γίνονταν
  //     κίτρινα με το raw channel_id — το bug του χρήστη.)
  const _noFilter = !ACTIVE_FILTER && selectedTags.size === 0 && searchRating === 0
                    && !(document.getElementById("search-input") || {}).value;
  const existingKeys = new Set(groups.keys());
  for (const cid of (_noFilter ? Object.keys(WATCHED_META) : [])) {
    if (existingKeys.has(cid)) continue;  // ήδη εμφανίζεται (έχει βίντεο)
    const meta = WATCHED_META[cid] || {};
    // 📛 Όνομα: meta.name → από τα βίντεο → «Άγνωστο κανάλι» (ΠΟΤΕ raw channel_id)
    const _vn = allVideos.find(x => x.channel_id === cid && x.channel);
    const name = meta.name || (_vn ? _vn.channel : "") || t('msg.unknownChannel');'''

if old in s:
    s = s.replace(old, new); n += 1; print("[OK] imported branch: μονο χωρις φιλτρο + σωστο ονομα")
else:
    print("[FAIL] imported branch")

open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
