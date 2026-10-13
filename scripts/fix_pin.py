"""togglePinChannel: load() -> στοχευμένη αλλαγή (το pin αλλάζει μόνο σειρά/ζώνη).
Ίδιο μοτίβο με το togglePinCategory."""
p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

old = '''function togglePinChannel(key, btn) {
  // 📌 Keep-στυλ: απλό toggle (pinned ↔ unpinned), χωρίς popup.
  fetch("/pin_channel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel_id: key }),
  }).then(r => r.json()).then(() => {
    // spring feedback στο κουμπί
    if (btn) { btn.classList.add("pinning"); }
    load();
  }).catch(() => {});
}'''

new = '''function togglePinChannel(key, btn) {
  // 📌 Keep-στυλ: απλό toggle (pinned ↔ unpinned), χωρίς popup.
  if (btn) { btn.classList.add("pinning"); }
  fetch("/pin_channel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ channel_id: key }),
  }).then(r => r.json()).then((d) => {
    // ⚡ Αντί για load() (fetch+render 3556 κάρτες): άλλαξε τη σειρά ΤΟΠΙΚΑ και
    //    ξαναχτίσε ΜΟΝΟ τη λίστα — χωρίς νέο fetch στο backend.
    try {
      const i = channelOrder.indexOf(key);
      if (i >= 0) channelOrder.splice(i, 1);
      if (d && d.pinned) channelOrder.unshift(key);
      else channelOrder.push(key);
    } catch (e) { /* ignore */ }
    renderCurrent();   // τοπικό re-render (χωρίς δίκτυο)
  }).catch(() => {});
}'''

if old in s:
    s = s.replace(old, new); n += 1
    print("[OK] togglePinChannel: χωρίς load() (χωρίς fetch ξαναφορτωμα)")
else:
    print("[FAIL] togglePinChannel")

open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
