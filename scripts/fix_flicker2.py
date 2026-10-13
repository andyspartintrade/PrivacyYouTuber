"""Μέρος 2: το no-anim στο re-render + λιγότερα περιττά re-renders."""
import re

p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

# ══ 1. renderCatPopList: βάλε no-anim (γιατί το popup είναι ΗΔΗ ανοιχτό) ══
old = '''  const _popEl = document.getElementById("cat-pop");
  if (_popEl) _popEl.classList.add("paged");'''
new = '''  const _popEl = document.getElementById("cat-pop");
  if (_popEl) { _popEl.classList.add("paged"); _popEl.classList.add("no-anim"); }  // 🚫 χωρίς επανάληψη animation'''
if old in s:
    s = s.replace(old, new); n += 1; print("[OK] cat render: no-anim")

old2 = '''  const _tagPopEl = document.getElementById("tag-pop");
  if (_tagPopEl) _tagPopEl.classList.add("paged");'''
new2 = '''  const _tagPopEl = document.getElementById("tag-pop");
  if (_tagPopEl) { _tagPopEl.classList.add("paged"); _tagPopEl.classList.add("no-anim"); }'''
if old2 in s:
    s = s.replace(old2, new2); n += 1; print("[OK] tag render: no-anim")

# ══ 2. Στο ΑΝΟΙΓΜΑ: βγάλε το no-anim (να παίξει ΚΑΝΟΝΙΚΑ το animation) ══
for fn in ("cat-pop", "tag-pop"):
    var = "_popEl" if fn == "cat-pop" else "_tagPopEl"
    # βρες το σημείο add("open")
    pat = 'pop.classList.add("open");'
    # Θα το χειριστούμε με ξεχωριστό replace παρακάτω

# Στο openCatPop:
old3 = '''  renderCatPopList(current);
  pop.classList.add("open");
  repositionCatPopSoon();'''
new3 = '''  pop.classList.remove("no-anim");   // ✅ ΤΩΡΑ να παίξει το animation εισόδου
  renderCatPopList(current);
  pop.classList.add("open");
  repositionCatPopSoon();'''
if old3 in s:
    s = s.replace(old3, new3); n += 1; print("[OK] openCatPop: remove no-anim")

# Στο openTagPop:
old4 = '''  pop.classList.remove("closing");
  pop.style.display = "";
  pop.classList.add("open");'''
new4 = '''  pop.classList.remove("closing");
  pop.classList.remove("no-anim");   // ✅ παίξε το animation εισόδου
  pop.style.display = "";
  pop.classList.add("open");'''
if old4 in s:
    s = s.replace(old4, new4); n += 1; print("[OK] openTagPop: remove no-anim")

open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
