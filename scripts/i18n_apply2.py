"""
Εφαρμοστής i18n — ΑΣΦΑΛΗΣ (χωρίς regex backreferences).
Χρησιμοποιεί ΣΚΕΤΟ str.replace() με ακριβή patterns.

A) placeholder="gr"  -> data-i18n-placeholder="key" placeholder="en"
B) title="gr"        -> data-i18n-title="key" title="en"
"""
import re, sys, json
sys.path.insert(0, "scripts")
from i18n_map import LEX

INDEX = "web/index.html"
html = open(INDEX, encoding="utf-8").read()

by_len = sorted(LEX.items(), key=lambda kv: -len(kv[0]))

changed = 0
def esc_attr(s):
    return s.replace('"', "&quot;")

# A placeholders
for gr, (key, en, el) in by_len:
    old = 'placeholder="' + gr + '"'
    new = 'data-i18n-placeholder="' + key + '" placeholder="' + esc_attr(en) + '"'
    if old in html:
        html = html.replace(old, new)
        changed += 1

# B titles
for gr, (key, en, el) in by_len:
    old = 'title="' + gr + '"'
    new = 'data-i18n-title="' + key + '" title="' + esc_attr(en) + '"'
    if old in html:
        html = html.replace(old, new)
        changed += 1

# C HTML text: >TXT<  ->  ><span data-i18n="key">EN</span><
for gr, (key, en, el) in by_len:
    old = ">" + gr + "<"
    new = '><span data-i18n="' + key + '">' + en + "</span><"
    if old in html:
        html = html.replace(old, new)
        changed += 1

open(INDEX, "w", encoding="utf-8").write(html)
print(f"Αλλαγές: {changed}")
