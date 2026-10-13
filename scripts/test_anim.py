"""Τεστ: μετράει τη θέση κατά τη ΔΙΑΡΚΕΙΑ και μετά το animation."""
import re, subprocess

h = open("web/index.html", encoding="utf-8").read()
css = re.search(r"<style>([\s\S]*?)</style>", h).group(1)

names = ["Photography", "Music Production", "Gaming", "Cooking", "Travel", "Tech Reviews"]
rows = "".join(
    f'<div class="tag-pop-item"><label class="tag-pop-label">'
    f'<input type="radio" name="cat-radio">{n}</label>'
    f'<button class="tag-del">×</button></div>' for n in names)

html = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>
<body style="background:#16181d;color:#eee;margin:0">
<button id="BTN" style="position:absolute;top:600px;left:400px">📁</button>
<div class="tag-pop" id="cat-pop">
  <div class="tag-pop-head">📁 Category</div>
  <div class="tag-pop-list" id="cat-pop-list"></div>
  <div class="tag-pop-new"><input placeholder="+ new"><button>Add</button></div>
</div>
<pre id="R" style="position:fixed;bottom:0;left:0;background:#000;font-size:11px"></pre>
<script>
const pop = document.getElementById("cat-pop");
const btn = document.getElementById("BTN");
const list = document.getElementById("cat-pop-list");
const log = [];

function reposition() {{
  const p = document.getElementById("cat-pop");
  if (!p.classList.contains("open") || !btn) return;
  const r = btn.getBoundingClientRect();
  const pw = p.getBoundingClientRect().width || 220;
  const ph = p.offsetHeight || 0;
  p.style.top = Math.max(8, Math.min(r.bottom + 6, window.innerHeight - ph - 8)) + "px";
  p.style.left = Math.max(8, Math.min(r.left, window.innerWidth - pw - 8)) + "px";
  log.push("t=" + Math.round(performance.now()) + " rect.top=" + Math.round(p.getBoundingClientRect().top) + " offsetH=" + ph);
}}

// ΓΕΜΙΣΕ
list.classList.add("paged");
list.innerHTML = '<div class="pop-page-grid">{rows}</div>';

// ΑΝΟΙΞΕ
pop.classList.add("open");
reposition();

// ΜΕΤΡΑ σε 0, 100, 300, 600 ms (κατά + μετά το animation)
[0, 100, 300, 600].forEach(ms => {{
  setTimeout(() => {{
    const p = document.getElementById("cat-pop");
    const r = p.getBoundingClientRect();
    log.push("@" + ms + "ms: top=" + Math.round(r.top) + " left=" + Math.round(r.left) + " style.top=" + (p.style.top||"-") + " style.left=" + (p.style.left||"-"));
    if (ms === 600) document.getElementById("R").textContent = log.join("\\n");
  }}, ms);
}});
</script></body></html>'''

open("scripts/_anim.html", "w", encoding="utf-8").write(html)
out = subprocess.run(
    [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
     "--headless", "--disable-gpu", "--window-size=1400,900", "--dump-dom",
     "file:///C:/Users/andys/privacy-yt/scripts/_anim.html"],
    capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
m = re.search(r'id="R"[^>]*>([\s\S]*?)</pre>', out)
print(m.group(1) if m else "ΔΕΝ ΒΡΕΘΗΚΕ")
