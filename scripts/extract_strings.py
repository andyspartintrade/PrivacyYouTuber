"""
Εξάγει τα ΠΡΑΓΜΑΤΙΚΑ ελληνικά UI strings (κείμενο σε HTML, placeholders, titles,
JS strings, popup messages) από το web/index.html — ΟΧΙ σχόλια κώδικα.
Τα γράφει σε ένα αρχείο για μετάφραση.
"""
import re
import json

SRC = "web/index.html"
OUT = "_ui_strings.json"

h = open(SRC, encoding="utf-8").read()
lines = h.split("\n")

greek_re = re.compile(r'[\u0370-\u03FF\u1F00-\u1FFF]')

found = []

def add(s):
    s = s.strip()
    if not s or not greek_re.search(s):
        return
    if s not in found:
        found.append(s)

for i, line in enumerate(lines):
    # 1. HTML text: >...<
    for m in re.finditer(r'>([^<>{}]*[\u0370-\u03FF][^<>{}]*)<', line):
        add(m.group(1))
    # 2. placeholder="..."
    for m in re.finditer(r'placeholder="([^"]*)"', line):
        add(m.group(1))
    # 3. title="..."
    for m in re.finditer(r'title="([^"]*)"', line):
        add(m.group(1))
    # 4. JS single/double quoted strings με ελληνικά
    for m in re.finditer(r'''["'`]([^"'`]*[\u0370-\u03FF][^"'`]*)["'`]''', line):
        txt = m.group(1)
        # παράλειψε αν είναι σχόλιο
        if '/*' in line and '*/' in line:
            core = re.sub(r'/\*.*?\*/', '', line)
            if m.group(1) not in core:
                continue
        add(txt)
    # 5. text after // σε HTML (HTML comments ΔΕΝ αλλάζουν — σκόπιμα skip)

json.dump(found, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"Βρέθηκαν {len(found)} μοναδικά UI strings → {OUT}")
print()
for s in found:
    print(repr(s))
