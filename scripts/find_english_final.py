"""
ΑΚΡΙΒΗΣ έλεγχος: αγγλικό UI ΧΩΡΙΣ data-i18n (άρα μένει αγγλικό σε el mode).
Διαβάζει το HTML tag-προς-tag και βλέπει αν έχει data-i18n* attribute.
"""
import re

h = open("web/index.html", encoding="utf-8").read()

# έλεγξε αν το tag που περιέχει αυτό το attr έχει data-i18n
def has_i18n(attr_pos):
    # πάρε το tag γύρω από τη θέση
    start = h.rfind("<", 0, attr_pos)
    if start < 0:
        return True
    end = h.find(">", attr_pos)
    tag = h[start:end if end > 0 else attr_pos + 100]
    return "data-i18n" in tag

missing = {"placeholder": [], "title": []}

for attr in ("placeholder", "title"):
    for m in re.finditer(attr + r'="([^"]{2,60})"', h):
        s = m.group(1)
        if not re.search(r"[A-Za-z]", s):
            continue
        if re.search(r"[\u0370-\u03FF]", s):
            continue
        if not has_i18n(m.start()):
            missing[attr].append(s)

# text nodes: βρες tags ΧΩΡΙΣ data-i18n που έχουν αγγλικό text
# (τα απλά: >TEXT< χωρίς nested tags)
missing["text"] = []
for m in re.finditer(r'>([^<>{}]{2,50})<', h):
    s = m.group(1).strip()
    if not s or not re.search(r"[A-Za-z]", s) or re.search(r"[\u0370-\u03FF]", s):
        continue
    if any(c in s for c in ("{", "}", ";", "px", "var(", "url(", "@", "/*")):
        continue
    if s.startswith(("/", ".", "#", "<!--")):
        continue
    # πάρε το tag πριν
    start = h.rfind("<", 0, m.start())
    tag = h[start:m.start()]
    if "data-i18n" in tag:
        continue
    missing["text"].append(s)

for k in missing:
    missing[k] = list(dict.fromkeys(missing[k]))

tot = 0
for k, lbl in (("placeholder", "PLACEHOLDER"), ("title", "TITLE"), ("text", "TEXT")):
    print(f"=== {lbl}: {len(missing[k])} ===")
    for s in missing[k]:
        print("  ", repr(s))
    tot += len(missing[k])
print(f"\nΣΥΝΟΛΟ ΧΩΡΙΣ i18n: {tot}")
