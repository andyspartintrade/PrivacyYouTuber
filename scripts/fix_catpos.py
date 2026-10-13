"""Διορθώνει το repositionCatPop (σπασμένο από bash) + προσθέτει data-id στα κουμπιά."""
import re

p = "web/index.html"
s = open(p, encoding="utf-8").read()

# ══ 1. Ξαναγράψε το repositionCatPop ΣΩΣΤΑ ══
old_fn = re.search(r"function repositionCatPop\(\) \{[\s\S]*?\n\}", s).group(0)

new_fn = '''function repositionCatPop() {
  const pop = document.getElementById("cat-pop");
  if (!pop.classList.contains("open") || !catPopTarget) return;
  // 🔄 ΑΝ το κουμπί αποκολλήθηκε (π.χ. re-render της λίστας), ΒΡΕΣ ΤΟ ΝΕΟ.
  if (!catPopBtn || !catPopBtn.isConnected) {
    catPopBtn = document.querySelector('.cat-btn[data-id="' + catPopTarget + '"]');
    if (!catPopBtn) catPopBtn = document.querySelector(".cat-btn");
    if (!catPopBtn || !catPopBtn.isConnected) return;   // δεν βρέθηκε → μη μετακινηθείς
  }
  const r = catPopBtn.getBoundingClientRect();
  if (r.width === 0 && r.height === 0) return;   // αποκολλημένο → ΟΧΙ (0,0)
  if (r.bottom < 0 || r.top > window.innerHeight) { closeCatPop(); return; }
  // 📏 offsetWidth/offsetHeight (layout box) — το animation pop-in έχει
  //    transform:scale() και το getBoundingClientRect δίνει ΟΠΤΙΚΟ μέγεθος.
  const pw = pop.offsetWidth || 220;
  const ph = pop.offsetHeight || 0;
  pop.style.top = Math.max(8, Math.min(r.bottom + 6, window.innerHeight - ph - 8)) + "px";
  pop.style.left = Math.max(8, Math.min(r.left, window.innerWidth - pw - 8)) + "px";
}'''

s = s.replace(old_fn, new_fn)
print("[OK] repositionCatPop ξαναγράφτηκε")

# ══ 2. Πρόσθεσε data-id στα cat-btn (για να βρίσκεται το σωστό κουμπί) ══
old_btn = '''<button class="icon-btn cat-btn" data-i18n-title="misc.category" title="Category" onclick="event.stopPropagation();openCatPop(this, '${esc(v.video_id)}')">'''
new_btn = '''<button class="icon-btn cat-btn" data-id="${esc(v.video_id)}" data-i18n-title="misc.category" title="Category" onclick="event.stopPropagation();openCatPop(this, '${esc(v.video_id)}')">'''
if old_btn in s:
    s = s.replace(old_btn, new_btn)
    print("[OK] data-id προστέθηκε στα cat-btn")
else:
    print("[FAIL] cat-btn δεν βρέθηκε")

# ══ 3. Ίδιο fix για τα tag-btn ══
old_fn2 = re.search(r"function repositionTagPop\(\) \{[\s\S]*?\n\}", s)
if old_fn2:
    new_fn2 = '''function repositionTagPop() {
  const pop = document.getElementById("tag-pop");
  if (!pop.classList.contains("open") || !tagPopTarget) return;
  if (!tagPopBtn || !tagPopBtn.isConnected) {
    tagPopBtn = document.querySelector('.tag-btn[data-id="' + tagPopTarget.id + '"]');
    if (!tagPopBtn) tagPopBtn = document.querySelector(".tag-btn");
    if (!tagPopBtn || !tagPopBtn.isConnected) return;
  }
  const r = tagPopBtn.getBoundingClientRect();
  if (r.width === 0 && r.height === 0) return;
  if (r.bottom < 0 || r.top > window.innerHeight) {
    pop.classList.remove("open");
    tagPopTarget = null;
    tagPopBtn = null;
    return;
  }
  const pw = pop.offsetWidth || 220;
  const ph = pop.offsetHeight || 0;
  pop.style.left = Math.max(8, Math.min(r.left, window.innerWidth - pw - 8)) + "px";
  pop.style.top = Math.max(8, Math.min(r.bottom + 6, window.innerHeight - ph - 8)) + "px";
}'''
    s = s.replace(old_fn2.group(0), new_fn2)
    print("[OK] repositionTagPop ξαναγράφτηκε")

open(p, "w", encoding="utf-8").write(s)
print("written")
