"""Στοχευμενη ενημερωση της ΚΑΡΤΑΣ οταν αλλαζουν tags βιντεο (χωρις φιλτρο):
  - ξαναφτιαξε τα CHIPS των tags στην καρτα (απο videoTags -> σεβεται αρνησεις)
  - ενημερωσε το κουμπι 🏷️ (has-tags)
  - αν υπαρχει ενεργο φιλτρο -> renderCurrent() (φιλτραρει: το βιντεο φευγει)
"""
p = "web/index.html"
s = open(p, encoding="utf-8").read()

old = '''  // ⚡ ΜΟΝΟ αν υπάρχει ΕΝΕΡΓΟ φιλτρο tag χρειαζεται ξαναχτισιμο η λιστα
  //    (αλλαζει ποια βιντεο εμφανιζονται). Αλλιως: κανενα re-render.
  if (selectedTags.size > 0) {
    renderCurrent();
  } else {
    updateVideoCardTags(tagPopTarget);   // στοχευμενα: μονο η εμφανιση tags της καρτας
  }
}'''

new = '''  // ⚡ Με ΕΝΕΡΓΟ φιλτρο: ξαναφιλτράρε (το βίντεο μπορεί να φύγει απ' τη λίστα).
  if (selectedTags.size > 0) {
    renderCurrent();
  } else {
    // Χωρίς φίλτρο: ενημέρωσε ΣΤΟΧΕΥΜΕΝΑ την κάρτα (chips + κουμπί) — χωρίς re-render όλης της λίστας.
    updateVideoCardTags(tagPopTarget);
    refreshCardChips(tagPopTarget);
  }
}

/* 🔄 Ξαναφτιάχνει ΜΟΝΟ τα chips των tags σε μία κάρτα βίντεο (σέβεται τις αρνήσεις). */
function refreshCardChips(target) {
  try {
    if (!target || target.type !== 'video') return;
    const v = allVideos.find(x => x.video_id === target.id);
    if (!v) return;
    const card = document.querySelector('.v-card[data-id="' + target.id + '"]');
    if (!card) return;
    const tags = videoTags(v);   // ✅ σεβεται tags καναλιου + αρνησεις ("-tag")
    const host = card.querySelector(".v-card-meta");
    if (!host) return;
    // Τα chips ζουν ΜΑΖΙ με το noteChip στο .v-card-meta → κρατάμε το noteChip, αλλάζουμε τα chips.
    const noteChip = host.querySelector(".note-chip");
    const noteHtml = noteChip ? noteChip.outerHTML : "";
    host.innerHTML = tags.map(t => {
      const on = selectedTags.has(t);
      return `<span class="tag-chip ${on ? 'match-chip' : ''}">${esc(t)}</span>`;
    }).join("") + noteHtml;
  } catch (e) { /* ignore */ }
}'''

if old in s:
    s = s.replace(old, new)
    print("[OK] toggleTag: στοχευμενη ενημερωση καρτας (chips+κουμπι)")
else:
    print("[FAIL] not found")

open(p, "w", encoding="utf-8").write(s)
print("done")
