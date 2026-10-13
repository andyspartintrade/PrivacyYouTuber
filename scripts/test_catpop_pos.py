"""Προσομοιώνει το openCatPop με πραγματικό Edge → μετράει top/left."""
import re, subprocess

h = open("web/index.html", encoding="utf-8").read()
css = re.search(r"<style>([\s\S]*?)</style>", h).group(1)

names = ["Photography", "Music Production", "Gaming", "Cooking", "Travel", "Tech Reviews"]
rows = "".join(
    f'<div class="tag-pop-item"><label class="tag-pop-label">'
    f'<input type="radio" name="cat-radio">{n}</label>'
    f'<button class="tag-del">×</button></div>' for n in names)

html = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>
<body style="background:#16181d;color:#eee;padding:0;margin:0">
<!-- Το κουμπί-στόχος (π.χ. 📁 σε κάρτα βίντεο) -->
<button id="BTN" style="position:absolute;top:600px;left:400px">📁</button>
<!-- Το popup ΟΠΩΣ στην εφαρμογή: ΜΟΝΟ class tag-pop, χωρίς inline style -->
<div class="tag-pop" id="cat-pop">
  <div class="tag-pop-head">📁 Category <button class="tag-pop-close">×</button></div>
  <div class="tag-pop-list" id="cat-pop-list"></div>
  <div class="tag-pop-new"><input placeholder="+ new category"><button>Add</button></div>
</div>
<pre id="R" style="position:fixed;bottom:0;left:0;background:#000"></pre>
<script>
// Προσομοίωση openCatPop (ΑΚΡΙΒΩΣ όπως ο κώδικας)
const pop = document.getElementById("cat-pop");
const btn = document.getElementById("BTN");
const list = document.getElementById("cat-pop-list");

function repositionCatPop() {{
  const p = document.getElementById("cat-pop");
  if (!p.classList.contains("open") || !btn) return;
  const r = btn.getBoundingClientRect();
  if (r.bottom < 0 || r.top > window.innerHeight) {{ return; }}
  p.style.top = Math.min(r.bottom + 6, window.innerHeight - p.offsetHeight - 8) + "px";
  p.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 300)) + "px";
}}

// 1) γέμισε το list (όπως renderCatPopList)
list.classList.add("paged");
list.innerHTML = '<div class="pop-page-grid">{rows}</div>';

// 2) add open
pop.classList.add("open");

// 3) ΜΕΤΡΑ ΠΡΙΝ το reposition
const beforeH = pop.offsetHeight;
const beforeRect = pop.getBoundingClientRect();

// 4) reposition
repositionCatPop();

// 5) ΜΕΤΡΑ ΜΕΤΑ
const afterRect = pop.getBoundingClientRect();
const cs = getComputedStyle(pop);

document.getElementById("R").textContent =
  "πριν: offsetH=" + beforeH +
  " rect.top=" + Math.round(beforeRect.top) + " rect.left=" + Math.round(beforeRect.left) +
  " || μετά: top=" + Math.round(afterRect.top) + " left=" + Math.round(afterRect.left) +
  " || style.top=" + pop.style.top + " style.left=" + pop.style.left +
  " || position=" + cs.position + " display=" + cs.display +
  " || btn: top=" + Math.round(btn.getBoundingClientRect().top) + " left=" + Math.round(btn.getBoundingClientRect().left);
</script></body></html>'''

open("scripts/_pos.html", "w", encoding="utf-8").write(html)

out = subprocess.run(
    [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
     "--headless", "--disable-gpu", "--window-size=1400,900", "--dump-dom",
     "file:///C:/Users/andys/privacy-yt/scripts/_pos.html"],
    capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
m = re.search(r'id="R"[^>]*>([^<]*)', out)
print(m.group(1) if m else "ΔΕΝ ΒΡΕΘΗΚΕ")
