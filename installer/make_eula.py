#!/usr/bin/env python
"""Μετατρέπει τα legal/EULA-*.md σε plain .txt για τον NSIS installer.

Ο NSIS δείχνει το .txt στην σελίδα «License Agreement».
Χρησιμοποιεί UTF-8 (ο installer είναι Unicode True).
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEGAL = os.path.join(ROOT, "legal")
OUT = os.path.join(HERE, "legal")
os.makedirs(OUT, exist_ok=True)

# Πίνακας: (πηγή, προορισμός, γλώσσα)
JOBS = [
    ("EULA-EN.md", "EULA-EN.txt", "en"),
    ("EULA-EL.md", "EULA-EL.txt", "el"),
]


def clean(md, lang):
    # Γραμμές διαχωρισμού: ━ -> =
    out = md.replace("\u2501", "=")
    # Bullets
    out = out.replace("\u2022", " -")
    # Emoji (τα βγάζουμε — ο NSIS δεν τα δείχνει καλά)
    out = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]\uFE0F?", "", out)
    # Κόβουμε το τελικό τμήμα συμφωνίας (το ξαναγράφουμε παρακάτω, μεταφρασμένο)
    # ώστε να μην έχουμε ΔΙΠΛΗ γραμμή αποδοχής στο .txt
    markers = [
        'By clicking "I Agree" during installation',
        "Κάνοντας κλικ στο κουμπί",
    ]
    for m in markers:
        i = out.find(m)
        if i > 0:
            # κόβουμε και την τελευταία γραμμή διαχωρισμού πριν το marker
            head = out[:i].rstrip()
            if head.endswith("=========================================================="):
                head = head[: -len("==========================================================")].rstrip()
            out = head
            break
    # Καταληκτική γραμμή συμφωνίας (μεταφρασμένη)
    if lang == "el":
        tail = "\n\nΠατώντας «Συμφωνώ» αποδέχεσαι τους παραπάνω όρους.\n"
    else:
        tail = '\n\nBy clicking "I Agree" you accept the terms above.\n'
    return out + tail


def main():
    ok = True
    for src, dst, lang in JOBS:
        p = os.path.join(LEGAL, src)
        if not os.path.exists(p):
            print(f"  [SKIP] λείπει: {p}")
            ok = False
            continue
        md = io.open(p, encoding="utf-8").read()
        txt = clean(md, lang)
        io.open(os.path.join(OUT, dst), "w", encoding="utf-8", newline="\r\n").write(txt)
        print(f"  [OK] {dst}  ({len(txt.splitlines())} γραμμές, {len(txt)} χαρ.)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
