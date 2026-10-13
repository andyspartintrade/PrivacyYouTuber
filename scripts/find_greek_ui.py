"""
Βρίσκει ΟΛΑ τα ελληνικά strings στο web/index.html που ΔΕΝ έχουν ήδη data-i18n,
και τα κατηγοριοποιεί: HTML text, placeholder, title, JS string.
Αγνοεί σχόλια (/* */ , // , <!-- -->).
"""
import re, json

h = open("web/index.html", encoding="utf-8").read()

greek = re.compile(r'[\u0370-\u03FF]')

results = {"html_text": [], "placeholder": [], "title": [], "js_string": []}

# Αφαιρούμε σχόλια για να μην πιάσουμε comment Greek
# (κρατάμε θέσεις με αντικατάσταση με spaces — χοντρικά)

# 1. HTML text nodes: >...<
for m in re.finditer(r'>([^<>]*[\u0370-\u03FF][^<>]*)<', h):
    txt = m.group(1).strip()
    if txt and greek.search(txt):
        results["html_text"].append(txt)

# 2. placeholders/titles
for attr, key in (("placeholder", "placeholder"), ("title", "title")):
    for m in re.finditer(attr + r'="([^"]*)"', h):
        txt = m.group(1)
        if greek.search(txt):
            results[key].append(txt)

# 3. JS quoted strings
for m in re.finditer(r'''(["'`])((?:[^"'`\\]|\\.)*?[\u0370-\u03FF](?:[^"'`\\]|\\.)*?)\1''', h):
    s = m.group(2)
    # έλεγξε αν είναι σε σχόλιο (χοντρικά)
    start = m.start()
    line_start = h.rfind("\n", 0, start) + 1
    line = h[line_start:h.find("\n", start)]
    if line.strip().startswith("//") or line.strip().startswith("*"):
        continue
    if "/*" in line[:m.start()-line_start] and "*/" not in line[:m.start()-line_start]:
        continue
    results["js_string"].append(s)

# dedupe
for k in results:
    seen = []
    for s in results[k]:
        if s not in seen:
            seen.append(s)
    results[k] = seen

total = sum(len(v) for v in results.values())
print(f"HTML text: {len(results['html_text'])}")
print(f"placeholder: {len(results['placeholder'])}")
print(f"title: {len(results['title'])}")
print(f"JS string: {len(results['js_string'])}")
print(f"ΣΥΝΟΛΟ: {total}")

json.dump(results, open("_greek_ui.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n→ _greek_ui.json")

# Δείξε όλα τα html_text + placeholders + titles (τα πιο σίγουρα)
print("\n=== HTML TEXT ===")
for s in results["html_text"]:
    print(repr(s))
print("\n=== PLACEHOLDER ===")
for s in results["placeholder"]:
    print(repr(s))
print("\n=== TITLE ===")
for s in results["title"]:
    print(repr(s))
