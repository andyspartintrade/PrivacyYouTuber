"""Pagination στα popups tags/categories — 60 ανά σελίδα (6 στήλες × 10 γραμμές)."""
p = 'web/index.html'
s = open(p, encoding='utf-8').read()

# ══ 1. TAG POPUP ══
old_tag = '''function renderTagPopList(currentTags) {
  const list = document.getElementById("tag-pop-list");
  if (!ALL_TAGS.length) {
    list.innerHTML = '<span class="muted" style="font-size:12px"><span data-i18n="tag.writeFirst">Write your first tag 👇</span></span>';
    return;
  }
  list.innerHTML = ALL_TAGS.map(t => `
    <div class="tag-pop-item">
      <label class="tag-pop-label">
        <input type="checkbox" value="${esc(t)}" ${currentTags.includes(t) ? 'checked' : ''} onchange="toggleTag()">${esc(t)}
      </label>
      <button class="tag-del" title="Delete tag everywhere" onclick="confirmDeleteTag('${esc(t)}', this)">×</button>
    </div>
  `).join("");
}'''

new_tag = '''// 📄 PAGINATION στα popups: 6 στήλες × 10 γραμμές = 60/σελίδα (ίδιο με τις αναζητήσεις).
const POP_PAGE_SIZE = 60;
let _tagPopPage = 0, _catPopPage = 0;
let _tagPopCurrent = [];

function _pagerHtml(page, total, fnName) {
  const pages = Math.max(1, Math.ceil(total / POP_PAGE_SIZE));
  if (pages <= 1) return "";
  const p = Math.min(page, pages - 1);
  return `<div class="pop-pager">
      <button ${p === 0 ? "disabled" : ""} onclick="${fnName}(${p - 1})" title="Previous">◀</button>
      <span class="pop-pager-lbl">${p + 1} / ${pages}</span>
      <button ${p >= pages - 1 ? "disabled" : ""} onclick="${fnName}(${p + 1})" title="Next">▶</button>
    </div>`;
}

function setTagPopPage(p) { _tagPopPage = Math.max(0, p); renderTagPopList(_tagPopCurrent); }
function setCatPopPage(p) { _catPopPage = Math.max(0, p); renderCatPopList(_catPopCurrent); }

function renderTagPopList(currentTags) {
  _tagPopCurrent = currentTags || [];
  const list = document.getElementById("tag-pop-list");
  if (!ALL_TAGS.length) {
    list.classList.remove("paged");
    list.innerHTML = '<span class="muted" style="font-size:12px"><span data-i18n="tag.writeFirst">Write your first tag 👇</span></span>';
    return;
  }
  const total = ALL_TAGS.length;
  const pages = Math.max(1, Math.ceil(total / POP_PAGE_SIZE));
  if (_tagPopPage > pages - 1) _tagPopPage = pages - 1;
  const slice = ALL_TAGS.slice(_tagPopPage * POP_PAGE_SIZE, (_tagPopPage + 1) * POP_PAGE_SIZE);
  list.classList.add("paged");
  list.innerHTML = `<div class="pop-page-grid">` + slice.map(t => `
    <div class="tag-pop-item">
      <label class="tag-pop-label">
        <input type="checkbox" value="${esc(t)}" ${_tagPopCurrent.includes(t) ? 'checked' : ''} onchange="toggleTag()"><span>${esc(t)}</span>
      </label>
      <button class="tag-del" title="Delete tag everywhere" onclick="confirmDeleteTag('${esc(t)}', this)">×</button>
    </div>
  `).join("") + `</div>` + _pagerHtml(_tagPopPage, total, "setTagPopPage");
  applyI18n(list);
}'''

if old_tag in s:
    s = s.replace(old_tag, new_tag)
    print('[OK] TAG popup pagination')
else:
    print('[FAIL] TAG popup')

# ══ 2. CAT POPUP ══
old_cat = '''function renderCatPopList(currentCat) {
  const list = document.getElementById("cat-pop-list");
  let html = `<div class="tag-pop-item">
      <label class="tag-pop-label">
        <input type="radio" name="cat-radio" value="" ${!currentCat ? 'checked' : ''} onchange="setVideoCategory('')"><span data-i18n="msg.noCategoryParen">(no category)</span>
      </label>
    </div>`;
  for (const c of ALL_CATEGORIES) {
    html += `<div class="tag-pop-item">
      <label class="tag-pop-label">
        <input type="radio" name="cat-radio" value="${esc(c)}" ${currentCat === c ? 'checked' : ''} onchange="setVideoCategory('${esc(c)}')">${esc(c)}
      </label>
      <button class="tag-del" title="Delete category everywhere" onclick="confirmDeleteCategory('${esc(c)}', this)">×</button>
    </div>`;
  }
  list.innerHTML = html;
  applyI18n(list);
}'''

new_cat = '''let _catPopCurrent = "";
function renderCatPopList(currentCat) {
  _catPopCurrent = currentCat || "";
  const list = document.getElementById("cat-pop-list");
  // Πρώτο item «(no category)» — πάντα ορατό, ΔΕΝ μπαίνει στο grid.
  let html = `<div class="tag-pop-item">
      <label class="tag-pop-label">
        <input type="radio" name="cat-radio" value="" ${!_catPopCurrent ? 'checked' : ''} onchange="setVideoCategory('')"><span data-i18n="msg.noCategoryParen">(no category)</span>
      </label>
    </div>`;
  const total = ALL_CATEGORIES.length;
  const pages = Math.max(1, Math.ceil(total / POP_PAGE_SIZE));
  if (_catPopPage > pages - 1) _catPopPage = pages - 1;
  const slice = ALL_CATEGORIES.slice(_catPopPage * POP_PAGE_SIZE, (_catPopPage + 1) * POP_PAGE_SIZE);
  if (total) {
    html += `<div class="pop-page-grid">` + slice.map(c => `
      <div class="tag-pop-item">
        <label class="tag-pop-label">
          <input type="radio" name="cat-radio" value="${esc(c)}" ${_catPopCurrent === c ? 'checked' : ''} onchange="setVideoCategory('${esc(c)}')"><span>${esc(c)}</span>
        </label>
        <button class="tag-del" title="Delete category everywhere" onclick="confirmDeleteCategory('${esc(c)}', this)">×</button>
      </div>`).join("") + `</div>` + _pagerHtml(_catPopPage, total, "setCatPopPage");
  }
  list.classList.add("paged");
  list.innerHTML = html;
  applyI18n(list);
}'''

if old_cat in s:
    s = s.replace(old_cat, new_cat)
    print('[OK] CAT popup pagination')
else:
    print('[FAIL] CAT popup')

open(p, 'w', encoding='utf-8').write(s)
print('written')
