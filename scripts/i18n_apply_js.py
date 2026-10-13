"""
Αντικαθιστά JS string literals με ελληνικά -> t('key').
ΜΟΝΟ όταν το string είναι ΟΛΟΚΛΗΡΟ το quoted literal (όχι μέρος κώδικα).
Δεν αγγίζει σχόλια.
"""
import re, sys, json
sys.path.insert(0, "scripts")
from i18n_map import LEX

INDEX = "web/index.html"
html = open(INDEX, encoding="utf-8").read()

# greek -> key, από μεγάλο σε μικρό (αποφυγή partial)
by_len = sorted(LEX.items(), key=lambda kv: -len(kv[0]))

changed = 0
for gr, (key, en, el) in by_len:
    # αντικατέστησε "gr" ή 'gr' -> t('key')  (ολόκληρο literal)
    for quote in ('"', "'"):
        pat = quote + re.escape(gr) + quote
        if pat in html:
            html = html.replace(pat, f"t('{key}')")
            changed += 1

open(INDEX, "w", encoding="utf-8").write(html)
print(f"JS replacements: {changed}")

# υπόλοιπα
rem = re.findall(r'(["\'])([^"\'\n]{2,80}[\u0370-\u03FF][^"\'\n]*?)\1', html)
uniq = [s for q,s in rem if s not in () and 'function' not in s and '{' not in s]
uniq = list(dict.fromkeys(uniq))
print(f"Υπόλοιπα JS strings: {len(uniq)}")
for s in uniq[:40]:
    print("  ", repr(s))
