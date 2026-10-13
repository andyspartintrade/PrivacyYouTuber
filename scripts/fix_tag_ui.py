"""UI μερος: το tag popup δειχνει/γραφει σωστα τα κληρονομημενα + εξαιρεσεις.

video ταργκετ:
  • checked  = tagStateFor(v, t) !== 'off'   (κληρονομημενα φαινονται τσεκαρισμενα)
  • στο onchange, γραφουμε:
      - αν ειναι ΚΛΗΡΟΝΟΜΗΜΕΝΟ και το ΞΕΤΣΕΚΑΡΕΙ  → προσθεσε '-'+t (εξαιρεση)
      - αν ειναι ΚΛΗΡΟΝΟΜΗΜΕΝΟ και το ΤΣΕΚΑΡΕΙ   → αφαιρεσε το '-'+t
      - αν ειναι ΔΙΚΟ ΤΟΥ                          → προσθεσε/αφαιρεσε το t
"""
p = "web/index.html"
s = open(p, encoding="utf-8").read()
n = 0

# ── 1. renderTagPopList: το checked υπολογιζεται με το tagStateFor ──
old = '''  list.innerHTML = `<div class="pop-page-grid">` + slice.map(t => `
    <div class="tag-pop-item">
      <label class="tag-pop-label">
        <input type="checkbox" value="${esc(t)}" ${_tagPopCurrent.includes(t) ? 'checked' : ''} onchange="toggleTag()">${esc(t)}
      </label>
      <button class="tag-del" title="Delete tag everywhere" onclick="confirmDeleteTag('${esc(t)}', this)">×</button>
    </div>
  `).join("") + `</div>` + _pagerHtml(_tagPopPage, total, "setTagPopPage");
  applyI18n(list);'''

new = '''  // 🔗 Για VIDEO: τα κληρονομημένα (από το κανάλι) φαίνονται ΤΣΕΚΑΡΙΣΜΕΝΑ.
  const _isVideo = tagPopTarget && tagPopTarget.type === 'video';
  const _vObj = _isVideo ? allVideos.find(x => x.video_id === tagPopTarget.id) : null;
  list.innerHTML = `<div class="pop-page-grid">` + slice.map(t => {
    const checked = _isVideo
      ? (_vObj ? tagStateFor(_vObj, t) !== "off" : _tagPopCurrent.includes(t))
      : _tagPopCurrent.includes(t);
    return `
    <div class="tag-pop-item">
      <label class="tag-pop-label">
        <input type="checkbox" value="${esc(t)}" ${checked ? 'checked' : ''} onchange="toggleTag()">${esc(t)}
      </label>
      <button class="tag-del" title="Delete tag everywhere" onclick="confirmDeleteTag('${esc(t)}', this)">×</button>
    </div>`;
  }).join("") + `</div>` + _pagerHtml(_tagPopPage, total, "setTagPopPage");
  applyI18n(list);'''
if old in s:
    s = s.replace(old, new); n += 1; print("[OK] renderTagPopList: checked με κληρονομια")
else:
    print("[FAIL] renderTagPopList")

# ── 2. toggleTag: μετατροπη checked -> my_tags με αρνησεις ──
old2 = '''  const checked = [...document.querySelectorAll("#tag-pop-list input:checked")].map(i => i.value);
  const url = tagPopTarget.type === 'video' ? '/set_video_tags' : '/set_channel_tags';
  const body = tagPopTarget.type === 'video'
    ? { video_id: tagPopTarget.id, tags: checked }
    : { channel_id: tagPopTarget.id, tags: checked };
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (tagPopTarget.type === 'video') {
    const v = allVideos.find(x => x.video_id === tagPopTarget.id);
    if (v) v.my_tags = checked;
  } else {
    CHANNEL_TAGS[tagPopTarget.id] = checked;
  }'''

new2 = '''  const checked = [...document.querySelectorAll("#tag-pop-list input:checked")].map(i => i.value);
  if (tagPopTarget.type === 'video') {
    // 🔗 ΚΛΗΡΟΝΟΜΙΑ + ΕΞΑΙΡΕΣΗ: κρατάμε τα tags του βίντεο ΚΑΙ τις αρνήσεις ("-tag").
    const v = allVideos.find(x => x.video_id === tagPopTarget.id);
    const key = (v && (v.channel_id || v.channel)) || "__unknown__";
    const chanTags = CHANNEL_TAGS[key] || [];
    const next = [];
    const allKnown = new Set([...ALL_TAGS, ...chanTags, ...checked]);
    for (const t of allKnown) {
      if (checked.includes(t)) {
        // Θέλει το tag: αν ΔΕΝ το κληρονομεί, γράψ' το ρητά (θετικό).
        if (!chanTags.includes(t)) next.push(t);
      } else {
        // ΔΕΝ το θέλει: αν το κληρονομεί, γράψε ΕΞΑΙΡΕΣΗ ("-tag").
        if (chanTags.includes(t)) next.push("-" + t);
      }
    }
    fetch("/set_video_tags", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: tagPopTarget.id, tags: next }) });
    if (v) v.my_tags = next;
  } else {
    fetch("/set_channel_tags", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel_id: tagPopTarget.id, tags: checked }) });
    CHANNEL_TAGS[tagPopTarget.id] = checked;
  }'''
if old2 in s:
    s = s.replace(old2, new2); n += 1; print("[OK] toggleTag: γραφει θετικα + εξαιρεσεις")
else:
    print("[FAIL] toggleTag")

open(p, "w", encoding="utf-8").write(s)
print("changes:", n)
