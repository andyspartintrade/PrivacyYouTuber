"""Το renderTagPopList: checked = κληρονομημενα φαινονται τσεκαρισμενα."""
p = "web/index.html"
s = open(p, encoding="utf-8").read()

old = '''  list.innerHTML = `<div class="pop-page-grid">` + slice.map(t => `
    <div class="tag-pop-item">
      <label class="tag-pop-label">
        <input type="checkbox" value="${esc(t)}" ${_tagPopCurrent.includes(t) ? 'checked' : ''} onchange="toggleTag()">${esc(t)}
      </label>
      <button class="tag-del" data-i18n-title="tag.delEverywhere" title="Delete tag everywhere" onclick="confirmDeleteTag('${esc(t)}', this)">×</button>
    </div>
  `).join("") + `</div>` + _pagerHtml(_tagPopPage, total, "setTagPopPage");
  applyI18n(list);'''

new = '''  // 🔗 Για VIDEO: τα ΚΛΗΡΟΝΟΜΗΜΕΝΑ (από το banner του καναλιού) φαίνονται ΤΣΕΚΑΡΙΣΜΕΝΑ.
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
      <button class="tag-del" data-i18n-title="tag.delEverywhere" title="Delete tag everywhere" onclick="confirmDeleteTag('${esc(t)}', this)">×</button>
    </div>`;
  }).join("") + `</div>` + _pagerHtml(_tagPopPage, total, "setTagPopPage");
  applyI18n(list);'''

if old in s:
    s = s.replace(old, new)
    print("[OK] renderTagPopList: checked με κληρονομια")
else:
    print("[FAIL] not found")

open(p, "w", encoding="utf-8").write(s)
print("done")
