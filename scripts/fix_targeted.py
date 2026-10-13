"""Στοχευμένη ενημέρωση: αντί για renderCurrent() (ξαναχτίζει 3556 κάρτες),
ενημέρωσε ΜΟΝΟ την κάρτα του βίντεο που άλλαξε κατηγορία."""
import re

p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

# ══ Το setVideoCategory: στοχευμένο update αντί για renderCurrent() ══
old = '''    if (!keepOpen) closeCatPop();          // ✅ μόνο όταν ΔΙΑΛΕΞΕΣ υπάρχουσα
    else { renderCatPopList(cat); repositionCatPopSoon(); }   // ✅ μένει ανοιχτό + νέα θέση
    renderCurrent();
    renderCategories();
  });
}'''

new = '''    if (!keepOpen) closeCatPop();          // ✅ μόνο όταν ΔΙΑΛΕΞΕΣ υπάρχουσα
    else { renderCatPopList(cat); repositionCatPopSoon(); }   // ✅ μένει ανοιχτό + νέα θέση
    // ⚡ ΣΤΟΧΕΥΜΕΝΗ ενημέρωση — ΜΗΝ ξαναχτίσεις 3556 κάρτες (flicker + κόστος).
    //    Ενημερώνεται ΜΟΝΟ η κάρτα αυτού του βίντεο (το χρώμα/ετικέτα κατηγορίας).
    updateVideoCardCategory(catPopTarget, cat);
    // Οι κατηγορίες ξαναχτίζονται ΜΟΝΟ αν προστέθηκε νέα (αλλιώς δεν άλλαξε κάτι ορατό).
    if (!_catDirty) { _catDirty = true; }
    if (currentTab === "categories") renderCategories();
  });
}

/* ⚡ Ενημερώνει ΜΟΝΟ την κάρτα ενός βίντεο (κατηγορία) — χωρίς re-render όλης της λίστας. */
function updateVideoCardCategory(videoId, cat) {
  try {
    const btn = document.querySelector('.cat-btn[data-id="' + videoId + '"]');
    if (!btn) return;
    const card = btn.closest(".v-card, .tag-pop-item, .video-card") || btn.parentElement;
    if (!card) return;
    // Το χρώμα/κατάσταση του κουμπιού κατηγορίας (αν το app το χρωματίζει)
    btn.classList.toggle("has-cat", !!cat);
    btn.title = cat ? (cat) : "Category";
    btn.setAttribute("data-cat", cat || "");
  } catch (e) { /* ignore */ }
}'''

if old in s:
    s = s.replace(old, new); n += 1; print("[OK] setVideoCategory: στοχευμενη ενημερωση")

open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
