"""
JS strings -> t('key'). ΑΣΦΑΛΕΣ: μόνο str.replace σε ακριβή quoted literals.
Δεν αγγίζει κώδικα (function/{/=>).
"""
import re, sys
sys.path.insert(0, "scripts")
from i18n_map import LEX

INDEX = "web/index.html"
html = open(INDEX, encoding="utf-8").read()
by_len = sorted(LEX.items(), key=lambda kv: -len(kv[0]))

changed = 0
for gr, (key, en, el) in by_len:
    if 'function' in gr or '{' in gr or len(gr) < 2 or len(gr) > 90:
        continue
    for q in ('"', "'"):
        old = q + gr + q
        if old in html:
            html = html.replace(old, "t('" + key + "')")
            changed += 1

open(INDEX, "w", encoding="utf-8").write(html)
print(f"JS replacements: {changed}")
