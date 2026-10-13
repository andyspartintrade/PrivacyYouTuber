"""
Διάγνωση: γιατί είναι «μπερδεμένα» τα popups/settings.

Ελέγχει 3 πράγματα:
  A) HTML text με ΕΛΛΗΝΙΚΑ που ΔΕΝ έχουν data-i18n  → μένουν ελληνικά σε EN mode
  B) HTML text με ΑΓΓΛΙΚΑ που ΔΕΝ έχουν data-i18n  → μένουν αγγλικά σε EL mode
  C) JS strings (σε popups/confirm) με ελληνικά ή αγγλικά χωρίς t()
"""
import re

h = open("web/index.html", encoding="utf-8").read()

print("=" * 70)
print("A) ΕΛΛΗΝΙΚΑ text nodes ΧΩΡΙΣ data-i18n (μένουν ελληνικά σε EN mode)")
print("=" * 70)
n = 0
for m in re.finditer(r'>([^<>]{2,80}[\u0370-\u03FF][^<>]*)<', h):
    s = m.group(1).strip()
    if not s:
        continue
    start = h.rfind("<", 0, m.start())
    tag = h[start:m.start()]
    if "data-i18n" in tag:
        continue
    # αγνόησε σχόλια
    line_start = h.rfind("\n", 0, m.start()) + 1
    line = h[line_start:h.find("\n", m.start())]
    if line.strip().startswith(("<!--", "//", "*")):
        continue
    n += 1
    print(f"  [{m.start()}] {s[:90]!r}")
print(f"  → ΣΥΝΟΛΟ: {n}")

print()
print("=" * 70)
print("B) ΑΓΓΛΙΚΑ text nodes ΧΩΡΙΣ data-i18n (μένουν αγγλικά σε EL mode)")
print("=" * 70)
n2 = 0
for m in re.finditer(r'>([^<>{}]{3,80})<', h):
    s = m.group(1).strip()
    if not s or not re.search(r"[A-Za-z]", s) or re.search(r"[\u0370-\u03FF]", s):
        continue
    if any(c in s for c in ("{", "}", ";", "px", "var(", "url(", "@")):
        continue
    if s.startswith(("/", ".", "#", "<!--")) or "=" in s:
        continue
    start = h.rfind("<", 0, m.start())
    tag = h[start:m.start()]
    if "data-i18n" in tag:
        continue
    line_start = h.rfind("\n", 0, m.start()) + 1
    line = h[line_start:h.find("\n", m.start())]
    if line.strip().startswith(("<!--", "//", "*")):
        continue
    n2 += 1
    print(f"  [{m.start()}] {s[:90]!r}")
print(f"  → ΣΥΝΟΛΟ: {n2}")
