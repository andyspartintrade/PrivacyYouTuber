"""
ΕΞΥΠΝΗ σάρωση: μόνο ΠΡΑΓΜΑΤΙΚΟ ορατό κείμενο (όχι σχόλια/κώδικας).

Τεχνική: αφαιρεί <script> και <style>, και μετά ψάχνει.
Για JS: αφαιρεί σχόλια γραμμής-προς-γραμμή.
"""
import re, json

h = open("web/index.html", encoding="utf-8").read()

# ═══ 1. HTML (εκτός script/style) ═══
masked = h
for tag in ("script", "style"):
    for m in re.finditer(rf"<{tag}[^>]*>.*?</{tag}>", h, re.S):
        masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]

print("=" * 70)
print("1) ΟΡΑΤΟ HTML ΚΕΙΜΕΝΟ ΜΕ ΕΛΛΗΝΙΚΑ (χωρίς i18n)")
print("=" * 70)
n = 0
for m in re.finditer(r">([^<>]{2,100}[\u0370-\u03FF][^<>]*)<", masked):
    s = m.group(1).strip()
    if not s:
        continue
    start = masked.rfind("<", 0, m.start())
    tag = masked[start:m.start()]
    if "data-i18n" in tag:
        continue
    n += 1
    print(f"  {s[:90]!r}")
print(f"  → {n}" if n else "  → ✅ ΚΑΘΑΡΟ")

print()
print("=" * 70)
print("2) JS STRINGS ΜΕ ΕΛΛΗΝΙΚΑ (καθαρά, όχι σχόλια, όχι κώδικας)")
print("=" * 70)
scripts = "\n".join(m.group(1) for m in re.finditer(r"<script>([\s\S]*?)</script>", h))
n2 = 0
seen = set()
for line in scripts.split("\n"):
    st = line.strip()
    if st.startswith("//") or st.startswith("*"):
        continue
    code = line.split("//")[0]
    for m in re.finditer(r'(["\'])((?:(?!\1)[^\\]|\\.){2,90})\1', code):
        s = m.group(2)
        if not re.search(r"[\u0370-\u03FF]", s):
            continue
        if s in seen or "function" in s or "=>" in s or "{" in s or "\\n" in s:
            continue
        seen.add(s)
        n2 += 1
        print(f"  {s[:90]!r}")
print(f"  → {n2}" if n2 else "  → ✅ ΚΑΘΑΡΟ")

print()
print("=" * 70)
print("3) data-i18n-title ΧΩΡΙΣ ελληνική μετάφραση (μένουν αγγλικά)")
print("=" * 70)
d = json.load(open("web/i18n.json", encoding="utf-8"))
keys = set(re.findall(r'data-i18n-title="([^"]+)"', h))
bad = [k for k in keys if k in d and d[k].get("en") == d[k].get("el")]
for k in sorted(bad):
    print(f"  {k}: {d[k].get('en')!r}")
print(f"  → {len(bad)}" if bad else "  → ✅ ΟΛΑ ΜΕΤΑΦΡΑΣΜΕΝΑ")
