#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ενημερώνει το PrivacyYouTuber draft στο Gumroad: 3 γλώσσες, διορθωμένο κείμενο.
ΑΟΡΑΤΟ (published=false). Τρέξε: python gumroad_update_draft.py
"""
import json, urllib.request, urllib.parse, ssl

ROOT = r'C:\Users\andys\privacy-yt'
PRODUCT_ID = 'sOap88TaNJAKelU4sjM4IQ=='   # το draft μας


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


EN = """<p><strong>⚠️ DIGITAL PRODUCT — READ BEFORE PURCHASING</strong></p>
<p>By completing your purchase, you expressly request the immediate delivery of the digital product (license key) and you waive your 14-day right of withdrawal (Article 16(m), Directive 2011/83/EU).</p>
<hr>
<p><strong>YOUTUBE, WITHOUT GOOGLE KNOWING ANYTHING ABOUT YOU.</strong></p>
<p>A Windows app that lets you search all of YouTube — and keep what you find, locally.</p>
<p>No account. No cloud. No tracking. No ads. Just your own machine.</p>
<h3>WHAT IT DOES</h3>
<ul>
<li><strong>Deep search</strong> — hundreds of results deep, not just the first 20.</li>
<li><strong>Your own library</strong> — every search is saved locally, with categories and pins.</li>
<li><strong>Your channels</strong> — add channels and organise your feed your way.</li>
<li><strong>Quick</strong> — opens in a few seconds, no installation required.</li>
</ul>
<h3>WHAT IT DOESN'T DO</h3>
<ul>
<li>❌ Sends nothing to anyone.</li>
<li>❌ No account required.</li>
<li>❌ No ads, no subscription.</li>
</ul>
<h3>WHAT YOU GET</h3>
<ul>
<li>PrivacyYouTuber for Windows (64-bit)</li>
<li>License for 1 computer (personal use)</li>
<li>Version 1.x updates</li>
<li>Email support</li>
</ul>
<p>Commercial or business use requires a separate license.</p>
<h3>REQUIREMENTS</h3>
<p>Windows 10 or 11 (64-bit) · 4 GB RAM · internet connection</p>
<h3>ONE CLARIFICATION</h3>
<p>PrivacyYouTuber is NOT affiliated with, endorsed by, or connected to YouTube or Google. It is an independent tool.</p>
<p>If something breaks: thawmaaa@gmail.com</p>"""

EL = """<h2>🇬🇷 ΕΛΛΗΝΙΚΑ</h2>
<p><strong>⚠️ ΑΓΟΡΑ ΨΗΦΙΑΚΟΥ ΠΡΟΪΟΝΤΟΣ — ΔΙΑΒΑΣΕ ΠΡΙΝ ΑΓΟΡΑΣΕΙΣ</strong></p>
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

DESC = EN + '\n<hr>\n' + EL


def main():
    data = {
        'description': DESC,
        'refund_period': 'none',
    }
    st, d = api('https://api.gumroad.com/v2/products/' + urllib.parse.quote(PRODUCT_ID, safe=''),
                method='PUT', data=data)
    print('HTTP', st)
    if d.get('success'):
        p = d['product']
        print('OK - UPDATED')
        for k in ['id', 'name', 'price', 'currency', 'published', 'refund_period']:
            print('   %-16s: %s' % (k, p.get(k)))
        print('   description len:', len(p.get('description') or ''))
    else:
        print('FAIL:', json.dumps(d, ensure_ascii=False)[:800])


if __name__ == '__main__':
    main()