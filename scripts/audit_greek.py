"""Έλεγχος: πόσα ελληνικά μένουν σε ΠΡΑΓΜΑΤΙΚΟ UI (όχι σχόλια/κώδικα)."""
import re

h = open('web/index.html', encoding='utf-8').read()
lines = h.split('\n')

# 1) HTML text nodes με ελληνικά (εκτός <script>)
# βρες τα script blocks και αγνόησέ τα
masked = h
for m in re.finditer(r'<script>.*?</script>', h, re.S):
    masked = masked[:m.start()] + ' ' * (m.end() - m.start()) + masked[m.end():]

html_txt = [s.strip() for s in re.findall(r'>([^<>]*[\u0370-\u03FF][^<>]*)<', masked)]
html_txt = [s for s in html_txt if s]

print(f"HTML text (εκτός script) με ελληνικά: {len(html_txt)}")
for s in html_txt[:25]:
    print("  ", repr(s[:100]))

# 2) JS strings (μέσα σε script), αγνοώντας σχόλια
print()
js_bad = []
for ln, line in enumerate(lines, 1):
    st = line.strip()
    if st.startswith('//') or st.startswith('*') or st.startswith('/*'):
        continue
    # αφαίρεσε inline comments (χοντρικά)
    code = line.split('//')[0]
    for m in re.finditer(r'(["\'])([^"\'\n]{2,90}[\u0370-\u03FF][^"\'\n]*?)\1', code):
        s = m.group(2)
        if 'function' in s or '{' in s or '=>' not in s and len(s) > 95:
            pass
        js_bad.append((ln, s))

print(f"JS strings με ελληνικά (καθαρά): {len(js_bad)}")
for ln, s in js_bad[:30]:
    print(f"  {ln}: {s[:90]!r}")
