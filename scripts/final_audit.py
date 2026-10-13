"""
ΤΕΛΙΚΟΣ ΕΛΕΓΧΟΣ — ψάχνει ΟΛΑ τα patterns που σπάσανε τη σελίδα:
  1. applyI18n μέσα σε .map(/.filter( callbacks
  2. data-i18n-title/-placeholder με interpolation ${...}
  3. keys στο i18n.json με " μέσα
  4. undefined vars σε applyI18n(...)
"""
import re, json

h = open("web/index.html", encoding="utf-8").read()
d = json.load(open("web/i18n.json", encoding="utf-8"))

print("=" * 60)
print("1) applyI18n ΜΕΣΑ σε .map()/.filter() callback;")
print("=" * 60)
bad = 0
for m in re.finditer(r"applyI18n\(", h):
    # πάρε τις 40 γραμμές πριν
    before = h[max(0, m.start()-3000):m.start()]
    # τελευταίο .map( ή .filter( χωρίς κλείσιμο
    opens = len(re.findall(r"\.(map|filter|forEach|reduce)\(", before))
    closes = before.count("})")
    if opens > closes:
        line = h[:m.start()].count("\n") + 1
        print(f"  ⚠️ γρ.{line}: πιθανό applyI18n μέσα σε callback")
        bad += 1
print(f"  → {bad} ύποπτα" if bad else "  → ✅ καθαρό")

print()
print("=" * 60)
print("2) data-i18n-title/-placeholder με ${} interpolation")
print("=" * 60)
bad2 = 0
for pat in (r'data-i18n-title="([^"]*)"', r'data-i18n-placeholder="([^"]*)"'):
    for m in re.finditer(pat, h):
        if "${" in m.group(1) or "&quot;" in m.group(1):
            line = h[:m.start()].count("\n") + 1
            print(f"  ⚠️ γρ.{line}: {m.group(1)[:70]}")
            bad2 += 1
print(f"  → {bad2} ύποπτα" if bad2 else "  → ✅ καθαρό")

print()
print("=" * 60)
print("3) keys στο i18n.json με \" μέσα")
print("=" * 60)
bad3 = [k for k, v in d.items() if '"' in v.get("en", "") or '"' in v.get("el", "")]
print(f"  → {bad3 if bad3 else '✅ ΚΑΝΕΝΑ'}")

print()
print("=" * 60)
print("4) applyI18n(...) με ΑΟΡΙΣΤΕΣ μεταβλητές")
print("=" * 60)
bad4 = 0
for m in re.finditer(r"applyI18n\(([^)]+)\)", h):
    arg = m.group(1).strip()
    if "||" in arg:
        line = h[:m.start()].count("\n") + 1
        print(f"  ⚠️ γρ.{line}: applyI18n({arg})")
        bad4 += 1
print(f"  → {bad4} ύποπτα" if bad4 else "  → ✅ καθαρό")

print()
total = bad + bad2 + len(bad3) + bad4
print("=" * 60)
print(f"ΣΥΝΟΛΟ ΠΡΟΒΛΗΜΑΤΩΝ: {total}")
print("=" * 60)
