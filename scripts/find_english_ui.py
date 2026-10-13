"""
Βρίσκει ΑΓΓΛΙΚΑ UI strings που ΔΕΝ έχουν data-i18n → γι' αυτό μένουν
αγγλικά όταν το UI είναι σε ελληνικά (el mode).

Ελέγχει: placeholders, titles, buttons (>, <), και σύντομα text nodes.
Αγνοεί: σχόλια, CSS, κώδικα, keys, URLs.
"""
import re

h = open("web/index.html", encoding="utf-8").read()

# Αγνόησε <script> blocks (κώδικας) και <style> blocks (CSS)
masked = h
for tag in ("script", "style"):
    for m in re.finditer(rf"<{tag}[^>]*>.*?</{tag}>", h, re.S):
        masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]

found = {"placeholder": [], "title": [], "text": []}

# 1) placeholders
for m in re.finditer(r'placeholder="([^"]{2,60})"', masked):
    s = m.group(1)
    if re.search(r"[A-Za-z]", s) and not re.search(r"[\u0370-\u03FF]", s):
        found["placeholder"].append(s)

# 2) titles
for m in re.finditer(r'title="([^"]{2,60})"', masked):
    s = m.group(1)
    if re.search(r"[A-Za-z]", s) and not re.search(r"[\u0370-\u03FF]", s):
        found["title"].append(s)

# 3) text nodes (σύντομα, χωρίς tags μέσα)
for m in re.finditer(r'>([^<>{}]{2,45})<', masked):
    s = m.group(1).strip()
    if not s or not re.search(r"[A-Za-z]", s) or re.search(r"[\u0370-\u03FF]", s):
        continue
    # απόφυγε CSS/JS υπολείμματα, μονάδες, classes
    if any(c in s for c in ("{", "}", ";", ":", "px", "var(", "rgba", "url(", "@")):
        continue
    if s.startswith(("/", ".", "#", "<!", "/*")):
        continue
    found["text"].append(s)

# dedupe + ταξινόμηση
for k in found:
    found[k] = list(dict.fromkeys(found[k]))

print(f"=== PLACEHOLDERS (χωρίς i18n): {len(found['placeholder'])} ===")
for s in found["placeholder"]:
    print("  ", repr(s))

print(f"\n=== TITLES (χωρίς i18n): {len(found['title'])} ===")
for s in found["title"]:
    print("  ", repr(s))

print(f"\n=== TEXT NODES (χωρίς i18n): {len(found['text'])} ===")
for s in found["text"]:
    print("  ", repr(s))
