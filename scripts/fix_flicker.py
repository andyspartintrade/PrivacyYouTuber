"""Διορθώνει το flicker όταν πατάς κατηγορία/tag."""
import re

p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

# ══ 1. Το reposition: ΜΙΑ φορά (όχι 3) ══
old = '''function repositionCatPopSoon() {
  requestAnimationFrame(() => requestAnimationFrame(() => repositionCatPop()));
  // ξανά μετά το animation (280ms) — ώστε η τελική θέση να είναι ΣΩΣΤΗ
  setTimeout(() => { try { repositionCatPop(); } catch (e) {} }, 300);
}'''
new = '''function repositionCatPopSoon() {
  // ΜΙΑ φορά, μετά το layout. (Το animation pop-in ΔΕΝ ξανατρέχει — βλ. renderCatPopList.)
  requestAnimationFrame(() => requestAnimationFrame(() => { try { repositionCatPop(); } catch (e) {} }));
}'''
if old in s:
    s = s.replace(old, new); n += 1; print("[OK] cat: ενα reposition (οχι 3)")

old2 = '''function repositionTagPopSoon() {
  requestAnimationFrame(() => requestAnimationFrame(() => repositionTagPop()));
  setTimeout(() => { try { repositionTagPop(); } catch (e) {} }, 300);
}'''
new2 = '''function repositionTagPopSoon() {
  requestAnimationFrame(() => requestAnimationFrame(() => { try { repositionTagPop(); } catch (e) {} }));
}'''
if old2 in s:
    s = s.replace(old2, new2); n += 1; print("[OK] tag: ενα reposition (οχι 3)")

# ══ 2. Το animation ΜΟΝΟ στο ΑΝΟΙΓΜΑ, όχι σε κάθε re-render του list ══
#    Κρατάμε το animation στο .open, αλλά το απενεργοποιούμε όταν το popup
#    είναι ήδη ανοιχτό (re-render περιεχομένου) → δεν ξανατρέχει.
old3 = '''  .tag-pop.open { display: block; animation: pop-in .28s cubic-bezier(.18,.9,.32,1.45); }'''
new3 = '''  .tag-pop.open { display: block; animation: pop-in .28s cubic-bezier(.18,.9,.32,1.45); }
  /* 🚫 ΧΩΡΙΣ επανάληψη animation όταν το popup είναι ΗΔΗ ανοιχτό (re-render
     περιεχομένου, π.χ. αλλαγή κατηγορίας/σελίδας) → δεν κάνει flicker. */
  .tag-pop.open.no-anim { animation: none; }'''
if old3 in s:
    s = s.replace(old3, new3); n += 1; print("[OK] CSS: .no-anim για ομαλό re-render")

open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
