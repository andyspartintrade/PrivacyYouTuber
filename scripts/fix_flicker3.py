"""Μέρος 3: περιττά re-renders — αν η κατηγορία ΔΕΝ άλλαξε, μην ξαναχτίζεις."""
import re

p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

# Το setVideoCategory: αν η κατηγορία είναι ΙΔΙΑ → μην κάνεις τίποτα (ούτε fetch)
old = '''function setVideoCategory(cat, keepOpen) {
  if (!catPopTarget) return;
  fetch("/set_category", {'''
new = '''function setVideoCategory(cat, keepOpen) {
  if (!catPopTarget) return;
  // 🚫 Αν η κατηγορία είναι ΙΔΙΑ με την τρέχουσα → τίποτα (αποφυγή flicker/re-render).
  const _cv = allVideos.find(x => x.video_id === catPopTarget);
  if (_cv && (_cv.category || "") === (cat || "")) {
    if (!keepOpen) closeCatPop();
    return;
  }
  fetch("/set_category", {'''
if old in s:
    s = s.replace(old, new); n += 1; print("[OK] setVideoCategory: skip αν ιδια")

# renderCategories: μην ξαναχτίσεις αν η κατηγορία δεν άλλαξε το σύνολο
# (το renderCategories είναι ακριβό — 3500 κάρτες)
open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
