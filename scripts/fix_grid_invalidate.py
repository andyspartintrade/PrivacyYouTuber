"""Καλει το invalidateChannelGrids() μεσα στο renderCurrent, ωστε
μετα απο καθε αλλαγη φιλτρου/tags να ξαναγεμιζουν τα grids των καναλιων."""
p = "web/index.html"
s = open(p, encoding="utf-8").read()

# 1) Στο renderCurrent, πριν το lazy fill:
old = '''  // ✅ LAZY: μετά το re-render, γέμισε τα grids των καναλιών που είναι ΑΝΟΙΧΤΑ.
  if (currentTab === "channels") {
    document.querySelectorAll("#videos .channel-group").forEach(grp => {
      if (!grp.classList.contains("collapsed")) fillChannelGrid(grp);
    });'''
new = '''  // ✅ LAZY: μετά το re-render, γέμισε τα grids των καναλιών που είναι ΑΝΟΙΧΤΑ.
  //    🔑 invalidate πρώτα: το φίλτρο/tags μπορεί να άλλαξαν → φρέσκα grids.
  try { invalidateChannelGrids(); } catch (e) {}
  if (currentTab === "channels") {
    document.querySelectorAll("#videos .channel-group").forEach(grp => {
      if (!grp.classList.contains("collapsed")) fillChannelGrid(grp);
    });'''
if old in s:
    s = s.replace(old, new)
    print("[OK] renderCurrent: invalidate grids πριν το fill")
else:
    print("[FAIL] renderCurrent")

# 2) Στο toggleTag: οταν αλλαζει tag βιντεο με ενεργο φιλτρο -> renderCurrent (ηδη),
#    οποτε το invalidate γινεται αυτοματα. Επιπλεον: οταν ΔΕΝ εχει φιλτρο,
#    το refreshCardChips φτανει.
open(p, "w", encoding="utf-8").write(s)
print("done")
