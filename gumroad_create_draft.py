#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Στήνει το PrivacyYouTuber ως ΑΟΡΑΤΟ draft στο Gumroad (published=false)."""
import json, sys, urllib.request, urllib.parse, ssl

ROOT = r'C:\Users\andys\privacy-yt'

def load_token():
    with open(ROOT + r'\.env', encoding='utf-8') as f:
        for line in f:
            if line.startswith('GUMROAD_ACCESS_TOKEN='):
                return line.split('=', 1)[1].strip()
    raise SystemExit('GUMROAD_ACCESS_TOKEN not found')

TOK = load_token()
CTX = ssl.create_default_context()

def api(url, method='GET', data=None):
    body = urllib.parse.urlencode(data, doseq=True).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method,
        headers={'Authorization': 'Bearer ' + TOK,
                 'User-Agent': 'PrivacyYouTuber/1.0'})
    try:
        r = urllib.request.urlopen(req, timeout=45, context=CTX)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'raw': raw[:400]}

DESC = """<p><strong>⚠️ ΑΓΟΡΑ ΨΗΦΙΑΚΟΥ ΠΡΟΪΟΝΤΟΣ — ΔΙΑΒΑΣΕ ΠΡΙΝ ΑΓΟΡΑΣΕΙΣ</strong></p>
<p>Με την ολοκλήρωση της αγοράς, ζητάς ρητά την άμεση παράδοση του ψηφιακού προϊόντος (κλειδί άδειας) και παραιτείσαι από το δικαίωμα υπαναχώρησης των 14 ημερών (Άρθρο 16(μ), Οδηγία 2011/83/ΕΕ).</p>
<hr>
<p><strong>ΤΟ YOUTUBE, ΧΩΡΙΣ ΝΑ ΜΑΘΑΙΝΕΙ ΤΙΠΟΤΑ ΓΙΑ ΣΕΝΑ.</strong></p>
<p>Μια εφαρμογή για Windows που σου επιτρέπει να ψάχνεις σε όλο το YouTube — και να κρατάς ό,τι βρίσκεις, τοπικά.</p>
<p>Δεν υπάρχει λογαριασμός. Δεν υπάρχει σύννεφο. Δεν υπάρχει tracking. Δεν υπάρχουν διαφημίσεις. Υπάρχει μόνο ο υπολογιστής σου.</p>
<h3>ΤΙ ΚΑΝΕΙ</h3>
<ul>
<li><strong>Βαθιά αναζήτηση</strong> — εκατοντάδες αποτελέσματα βάθους, όχι μόνο τα πρώτα 20.</li>
<li><strong>Η δική σου βιβλιοθήκη</strong> — κάθε αναζήτηση αποθηκεύεται τοπικά, με κατηγορίες και καρφιτσώματα.</li>
<li><strong>Τα κανάλια σου</strong> — προσθέτεις κανάλια και οργανώνεις τη ροή σου.</li>
<li><strong>Γρήγορη</strong> — ανοίγει σε λίγα δευτερόλεπτα, χωρίς εγκατάσταση.</li>
</ul>
<h3>ΤΙ ΔΕΝ ΚΑΝΕΙ</h3>
<ul>
<li>❌ Δεν στέλνει τίποτα σε κανέναν.</li>
<li>❌ Δεν ζητάει λογαριασμό.</li>
<li>❌ Δεν έχει διαφημίσεις ούτε συνδρομή.</li>
</ul>
<h3>ΤΙ ΠΑΙΡΝΕΙΣ</h3>
<ul>
<li>PrivacyYouTuber for Windows (64-bit)</li>
<li>Άδεια χρήσης για 1 υπολογιστή (προσωπική χρήση)</li>
<li>Ενημερώσεις έκδοσης 1.x</li>
<li>Υποστήριξη μέσω email</li>
</ul>
<p>Για επαγγελματική/εταιρική χρήση απαιτείται ξεχωριστή άδεια.</p>
<h3>ΑΠΑΙΤΗΣΕΙΣ</h3>
<p>Windows 10 ή 11 (64-bit) · 4 GB RAM · σύνδεση στο internet</p>
<h3>ΜΙΑ ΔΙΕΥΚΡΙΝΙΣΗ</h3>
<p>Το PrivacyYouTuber ΔΕΝ συνδέεται με το YouTube ή την Google. Είναι ανεξάρτητο εργαλείο.</p>
<p>Αν κάτι δεν δουλέψει: thawmaaa@gmail.com</p>"""

def main():
    data = {
        'name': 'PrivacyYouTuber — Το YouTube χωρίς ίχνη',
        'description': DESC,
        'price': '1499',
        'price_currency_type': 'eur',
        'draft': 'true',
        'native_type': 'digital',
        'refund_period': 'none',
        # ΣΗΜΕΙΩΣΗ: το API απαιτεί tags ως array από strings. Με urlencode δεν
        # περνά σωστά σε αυτό το endpoint — τα βάζουμε αργότερα με PUT, ή
        # χρησιμοποιούμε json body. Για τώρα τα παραλείπουμε (δεν είναι critical).
    }
    st, d = api('https://api.gumroad.com/v2/products', method='POST', data=data)
    print('HTTP', st)
    if d.get('success'):
        p = d['product']
        print('OK - DRAFT CREATED')
        for k in ['id', 'name', 'price', 'currency', 'formatted_price',
                  'published', 'preview_url', 'short_url']:
            print('   %-16s: %s' % (k, p.get(k)))
        if d.get('warning'):
            print('   WARNING:', d['warning'])
    else:
        print('FAIL:', json.dumps(d, ensure_ascii=False)[:800])

if __name__ == '__main__':
    main()