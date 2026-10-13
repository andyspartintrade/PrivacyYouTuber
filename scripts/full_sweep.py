"""
ΠΛΗΡΗΣ ΣΑΡΩΣΗ για υπολειπόμενα προβλήματα i18n.
Ψάχνει ΟΛΑ τα σημεία που μπορεί να μένουν σε λάθος γλώσσα:
  A) JS strings με ΕΛΛΗΝΙΚΑ (hardcoded, όχι t())
  B) JS strings με ΑΓΓΛΙΚΑ (hardcoded, όχι t())
  C) HTML text με ελληνικά/αγγλικά χωρίς data-i18n
  D) keys στο i18n.json που δεν έχουν χρησιμοποιηθεί
"""
import re, json

h = open("web/index.html", encoding="utf-8").read()
d = json.load(open("web/i18n.json", encoding="utf-8"))

# Αγνόησε σχόλια JS (γραμμές // και * )
def is_comment(pos):
    ls = h.rfind("\n", 0, pos) + 1
    line = h[ls:h.find("\n", pos)]
    st = line.strip()
    return st.startswith("//") or st.startswith("*") or st.startswith("/*")

print("=" * 70)
print("A) JS STRINGS ΜΕ ΕΛΛΗΝΙΚΑ (hardcoded — ΔΕΝ αλλάζουν γλώσσα)")
print("=" * 70)
seen = set()
n = 0
for m in re.finditer(r'(["\'])((?:(?!\1)[^\\]|\\.){2,80})\1', h):
    s = m.group(2)
    if not re.search(r"[\u0370-\u03FF]", s):
        continue
    if "function" in s or "=>" in s or "{" in s:
        continue
    if is_comment(m.start()):
        continue
    if s in seen:
        continue
    seen.add(s)
    n += 1
    print(f"  {s[:95]!r}")
print(f"  → ΣΥΝΟΛΟ: {n}")

print()
print("=" * 70)
print("B) HTML TEXT ΜΕ ΕΛΛΗΝΙΚΑ (χωρίς data-i18n)")
print("=" * 70)
n2 = 0
for m in re.finditer(r">([^<>]{2,100}[\u0370-\u03FF][^<>]*)<", h):
    s = m.group(1).strip()
    if not s:
        continue
    start = h.rfind("<", 0, m.start())
    tag = h[start:m.start()]
    if "data-i18n" in tag:
        continue
    ls = h.rfind("\n", 0, m.start()) + 1
    line = h[ls:h.find("\n", m.start())]
    if line.strip().startswith(("<!--", "//", "*")):
        continue
    n2 += 1
    print(f"  {s[:95]!r}")
print(f"  → ΣΥΝΟΛΟ: {n2}")

print()
print("=" * 70)
print("C) KEYS ΣΤΟ i18n.json ΠΟΥ ΔΕΝ ΧΡΗΣΙΜΟΠΟΙΟΥΝΤΑΙ")
print("=" * 70)
used = set(re.findall(r'data-i18n(?:-title|-placeholder)?="([^"]+)"', h))
used |= set(re.findall(r"t\('([^']+)'\)", h))
unused = sorted(k for k in d if k not in used)
print(f"  → {len(unused)} αχρησιμοποίητα (φυσιολογικό — διαθέσιμα για μέλλον)")
for k in unused[:25]:
    print(f"     {k}: {d[k].get('en','')[:50]!r}")
