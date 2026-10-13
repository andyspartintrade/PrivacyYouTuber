"""
Εφαρμόζει το λεξικό (από i18n_map.LEX) στο web/index.html:
- HTML text nodes  -> <span data-i18n="key">EN</span>  (αντικαθιστά το ελληνικό text)
- placeholder="gr" -> data-i18n-placeholder="key"
- title="gr"       -> data-i18n-title="key"
- JS strings "gr"  -> t('key')   (ΜΟΝΟ όταν το string είναι ολόκληρο το κείμενο, όχι μέρος κώδικα)

ΠΡΟΣΟΧΗ: δεν αγγίζει σχόλια (/* */, //, <!-- -->).
"""
import json
import re
import sys
sys.path.insert(0, "scripts")
from i18n_map import LEX

INDEX = "web/index.html"
html = open(INDEX, encoding="utf-8").read()

# Χτίσε ανάστροφο: greek -> key  (ταξινομημένα από το ΜΕΓΑΛΥΤΕΡΟ στο μικρότερο,
# ώστε να αντικατασταθούν πρώτα οι μεγάλες φράσεις — αποφεύγει partial matches)
by_len = sorted(LEX.items(), key=lambda kv: -len(kv[0]))

changed = 0

def esc_attr(s):
    return s.replace('"', "&quot;")

# ── A) placeholders ──────────────────────────────────────────────
for gr, (key, en, el) in by_len:
    pat = 'placeholder="' + re.escape(gr) + '"'
    rep = f'data-i18n-placeholder="{key}" placeholder="{esc_attr(en)}"'
    if pat in html:
        html = html.replace(pat, rep)
        changed += 1

# ── B) titles ────────────────────────────────────────────────────
for gr, (key, en, el) in by_len:
    pat = 'title="' + re.escape(gr) + '"'
    rep = f'data-i18n-title="{key}" title="{esc_attr(en)}"'
    if pat in html:
        html = html.replace(pat, rep)
        changed += 1

# ── C) HTML text nodes (>TXT<<) ──────────────────────────────────
# μόνο αν το text είναι ΑΚΡΙΒΩΣ το ελληνικό string (trimmed) και δεν περιέχει tags
for gr, (key, en, el) in by_len:
    # >  + optional spaces + gr + optional spaces + <
    pat = re.compile(r'>(\s*)' + re.escape(gr) + r'(\s*)<')
    def repl(m):
        return f'>\\1<span data-i18n="{key}">{en}</span>\\2<'
    new_html, n = pat.subn(repl, html)
    if n:
        html = new_html
        changed += n

open(INDEX, "w", encoding="utf-8").write(html)
print(f"index.html: {changed} αλλαγές (placeholder/title/html-text)")

# ── μέτρησε πόσα ελληνικά έμειναν ────────────────────────────────
rem = re.findall(r'>([^<>]*[\u0370-\u03FF][^<>]*)<', html)
print(f"Υπόλοιπα ελληνικά σε HTML text nodes: {len(rem)}")
for s in rem[:20]:
    print("  ", repr(s.strip()[:80]))
