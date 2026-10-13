"""
Εξάγει την renderCatPopList + το CSS τους και φτιάχνει ένα αυτόνομο HTML
για να δω (με browser ή με έλεγχο κειμένου) τι παράγει.
"""
import re

h = open("web/index.html", encoding="utf-8").read()

# 1. Πάρε το CSS: ό,τι είναι μέσα στο <style>...</style>
style = re.search(r"<style>([\s\S]*?)</style>", h)
css = style.group(1) if style else ""

# 2. Πάρε το script
script = "\n".join(m.group(1) for m in re.finditer(r"<script>([\s\S]*?)</script>", h))

# 3. Φτιάξε αυτόνομο HTML με την renderCatPopList
test_html = """<!doctype html><html><head><meta charset="utf-8">
<style>
""" + css + """
</style></head><body style="background:#16181d;color:#eee;font-family:sans-serif;padding:40px">
<div class="tag-pop open paged" id="cat-pop" style="position:relative;display:block">
  <div class="tag-pop-head">📁 Category <button class="tag-pop-close">×</button></div>
  <div class="tag-pop-list" id="cat-pop-list"></div>
  <div class="tag-pop-new">
    <input type="text" placeholder="+ new category">
    <button>Add</button>
  </div>
</div>
<script>
// ── Ελάχιστο περιβάλλον ──
const esc = (s) => String(s);
const ALL_CATEGORIES = ["Photography","Music Production","Gaming","Cooking","Travel"];
const POP_PAGE_SIZE = 60;
let _catPopPage = 0;
let _catPopCurrent = "";
const t = (k) => k;
const applyI18n = () => {};

function _pagerHtml(page, total, fnName) {
  const pages = Math.max(1, Math.ceil(total / POP_PAGE_SIZE));
  if (pages <= 1) return "";
  const p = Math.min(page, pages - 1);
  return `<div class="pop-pager">
      <button ${p === 0 ? "disabled" : ""} onclick="${fnName}(${p - 1})">◀</button>
      <span class="pop-pager-lbl">${p + 1} / ${pages}</span>
      <button ${p >= pages - 1 ? "disabled" : ""} onclick="${fnName}(${p + 1})">▶</button>
    </div>`;
}

function renderCatPopList(currentCat) {
  _catPopCurrent = currentCat || "";
  const list = document.getElementById("cat-pop-list");
  let html = `<div class="tag-pop-item">
      <label class="tag-pop-label">
        <input type="radio" name="cat-radio" value="">(no category)
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
          <input type="radio" name="cat-radio" value="${esc(c)}">${esc(c)}
        </label>
        <button class="tag-del">×</button>
      </div>`).join("") + `</div>` + _pagerHtml(_catPopPage, total, "setCatPopPage");
  }
  list.classList.add("paged");
  list.innerHTML = html;
}

renderCatPopList("");

// ── ΕΛΕΓΧΟΙ ──
setTimeout(() => {
  const out = [];
  const list = document.getElementById("cat-pop-list");
  const grid = document.querySelector(".pop-page-grid");
  const pop = document.getElementById("cat-pop");
  out.push("list.className = " + list.className);
  out.push("grid υπάρχει: " + !!grid);
  if (grid) {
    const cs = getComputedStyle(grid);
    out.push("grid.display = " + cs.display);
    out.push("grid.gridTemplateColumns = " + cs.gridTemplateColumns);
    out.push("grid πλάτος = " + grid.getBoundingClientRect().width);
  }
  out.push("pop πλάτος = " + pop.getBoundingClientRect().width);
  const firstLabel = document.querySelector(".pop-page-grid .tag-pop-label");
  if (firstLabel) {
    out.push("label πλάτος = " + firstLabel.getBoundingClientRect().width);
    out.push("label textContent = '" + firstLabel.textContent.trim() + "'");
    const sp = firstLabel.querySelector("span");
    out.push("έχει span: " + !!sp);
  }
  // Δες τα items
  const items = document.querySelectorAll(".pop-page-grid .tag-pop-item");
  out.push("items: " + items.length);
  items.forEach((it, i) => {
    out.push(`  item[${i}] text='${it.textContent.trim()}' width=${it.getBoundingClientRect().width}`);
  });
  document.title = "DONE";
  window.__RESULT = out.join("\\n");
  document.body.setAttribute("data-result", out.join("\\n"));
  console.log(out.join("\\n"));
}, 100);
</script>
</body></html>"""

open("scripts/_catpop_test.html", "w", encoding="utf-8").write(test_html)
print("✅ Φτιάχτηκε: scripts/_catpop_test.html")
print("   CSS chars:", len(css))
