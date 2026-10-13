"""Tag inheritance + per-video exclusion.

ΛΟΓΙΚΗ (απαίτηση χρήστη 14/10/2026):
  • Tag στο BANNER του καναλιού → κληρονομείται από ΟΛΑ τα βίντεο (εμφανίζονται όλα).
  • Tag μόνο σε ΒΙΝΤΕΟ → μόνο αυτό εμφανίζεται.
  • Ξετσεκάροντας ένα ΚΛΗΡΟΝΟΜΗΜΕΝΟ tag σε ένα βίντεο → το βίντεο φεύγει από το φίλτρο.

ΥΛΟΠΟΙΗΣΗ: το `my_tags` κρατά ΚΑΙ αρνήσεις, ως "-tagname".
  videoTags(v) = (CHANNEL_TAGS + my_tags θετικά) − (my_tags αρνητικά)
"""
p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

# ══ 1. videoTags: σέβασέ τις αρνήσεις ══
old = '''function videoTags(v) {
  const set = new Set(v.my_tags || []);
  const key = v.channel_id || v.channel || "__unknown__";
  for (const t of (CHANNEL_TAGS[key] || [])) set.add(t);
  return [...set];
}'''
new = '''function videoTags(v) {
  const key = v.channel_id || v.channel || "__unknown__";
  const mine = (v.my_tags || []);
  const set = new Set();
  // 1) Πρόσθεσε τα ΚΛΗΡΟΝΟΜΗΜΕΝΑ (tags καναλιού)
  for (const t of (CHANNEL_TAGS[key] || [])) set.add(t);
  // 2) Πρόσθεσε τα δικά του (θετικά)
  for (const t of mine) if (t && t[0] !== "-") set.add(t);
  // 3) ΑΦΑΙΡΕΣΕ τα αρνητικά (εξαιρέσεις: «-music» = μη μου βάλεις το music)
  for (const t of mine) if (t && t[0] === "-") set.delete(t.slice(1));
  return [...set];
}

// Επιστρέφει το «κατάσταση» ενός tag για το tag-popup: 'on' | 'off' | 'inherited'
function tagStateFor(v, tag) {
  const mine = (v.my_tags || []);
  const key = v.channel_id || v.channel || "__unknown__";
  if (mine.includes("-" + tag)) return "off";        // το απέκλεισε ρητά
  if (mine.includes(tag)) return "on";                // δικό του
  if ((CHANNEL_TAGS[key] || []).includes(tag)) return "inherited";  // από το κανάλι
  return "off";
}'''
if old in s:
    s = s.replace(old, new); n += 1; print("[OK] videoTags: υποστηριζει αρνησεις")
else:
    print("[FAIL] videoTags")

open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
