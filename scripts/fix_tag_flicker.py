"""Το tag κανει renderCurrent() (ξαναχτιζει 3556 καρτες) -> ιδιο flicker.
Το κανουμε στοχευμενο, οπως την κατηγορια."""
import re

p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

# ── toggleTag: στοχευμενη ενημερωση αντι για renderCurrent() ──
old = '''  if (tagPopTarget.type === 'video') {
    const v = allVideos.find(x => x.video_id === tagPopTarget.id);
    if (v) v.my_tags = checked;
  } else {
    CHANNEL_TAGS[tagPopTarget.id] = checked;
  }
  // ξανατρέξε το ενεργό φίλτρο (αν υπάρχει) με τα νέα tags
  renderCurrent();
}'''
new = '''  if (tagPopTarget.type === 'video') {
    const v = allVideos.find(x => x.video_id === tagPopTarget.id);
    if (v) v.my_tags = checked;
  } else {
    CHANNEL_TAGS[tagPopTarget.id] = checked;
  }
  // ⚡ ΜΟΝΟ αν υπάρχει ΕΝΕΡΓΟ φιλτρο tag χρειαζεται ξαναχτισιμο η λιστα
  //    (αλλαζει ποια βιντεο εμφανιζονται). Αλλιως: κανενα re-render.
  if (selectedTags.size > 0) {
    renderCurrent();
  } else {
    updateVideoCardTags(tagPopTarget);   // στοχευμενα: μονο η εμφανιση tags της καρτας
  }
}

/* ⚡ Ενημερωνει ΜΟΝΟ την καρτα ενος στοιχειου (εμφανιση tags) — χωρις re-render. */
function updateVideoCardTags(target) {
  try {
    if (!target) return;
    if (target.type === 'video') {
      const btn = document.querySelector('.tag-btn[data-id="' + target.id + '"]');
      if (!btn) return;
      const v = allVideos.find(x => x.video_id === target.id);
      btn.classList.toggle("has-tags", !!(v && v.my_tags && v.my_tags.length));
    } else {
      const btn = document.querySelector('.tag-btn[data-id="' + target.id + '"]');
      if (!btn) return;
      const t = CHANNEL_TAGS[target.id] || [];
      btn.classList.toggle("has-tags", t.length > 0);
    }
  } catch (e) { /* ignore */ }
}'''
if old in s:
    s = s.replace(old, new); n += 1; print("[OK] toggleTag: στοχευμενη ενημερωση")

open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
