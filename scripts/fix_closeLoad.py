"""Αφαιρεί το load() από το closeTagPop (προκαλεί flicker — ξαναχτίζει 3556 κάρτες).
Το load() ήταν κατάλοιπο: τα tags πλέον ενημερώνονται στοχευμένα εκεί που αλλάζουν."""
p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

old = '''function closeTagPop() {
  const pop = document.getElementById("tag-pop");
  // Pop-out animation πριν το πραγματικό κλείσιμο.
  if (pop.classList.contains("open") && !pop.classList.contains("closing")) {
    pop.classList.remove("open");
    pop.classList.add("closing");
    setTimeout(() => {
      pop.classList.remove("closing");
      pop.style.display = "none";
      tagPopTarget = null;
      tagPopBtn = null;
      load();
    }, 150);
    return;
  }
  pop.classList.remove("open");
  tagPopTarget = null;
  tagPopBtn = null;
  load();
}'''

new = '''function closeTagPop() {
  const pop = document.getElementById("tag-pop");
  // Pop-out animation πριν το πραγματικό κλείσιμο.
  // 🚫 ΚΑΝΕΝΑ load() εδώ: ξαναέχτιζε 3556 κάρτες → flicker σε κάθε κλείσιμο.
  //    Τα tags ενημερώνονται στοχευμένα στο toggleTag (ή με renderCurrent ΜΟΝΟ
  //    όταν υπάρχει ενεργό φίλτρο tag).
  if (pop.classList.contains("open") && !pop.classList.contains("closing")) {
    pop.classList.remove("open");
    pop.classList.add("closing");
    setTimeout(() => {
      pop.classList.remove("closing");
      pop.style.display = "none";
      tagPopTarget = null;
      tagPopBtn = null;
    }, 150);
    return;
  }
  pop.classList.remove("open");
  pop.style.display = "none";
  tagPopTarget = null;
  tagPopBtn = null;
}'''

if old in s:
    s = s.replace(old, new); n += 1
    print("[OK] closeTagPop: load() αφαιρέθηκε")
else:
    print("[FAIL] closeTagPop δεν βρέθηκε")

# ── Έλεγξε αν αλλού το load() είναι περιττό ──
import re
for m in re.finditer(r"^function (\w+)\([^)]*\) \{", s, re.M):
    fn = m.group(1)
    body_start = m.end()
    body_end = s.find("\n}", body_start)
    body = s[body_start:body_end]
    if "load();" in body:
        print(f"  ℹ️ το {fn}() καλεί load()")

open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
