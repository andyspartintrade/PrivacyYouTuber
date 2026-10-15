#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Στήνει το νέο διαφημιστικό κείμενο (v2) στο PrivacyYouTuber draft.
ΑΟΡΑΤΟ (published=false). Τρέξε: python gumroad_update_copy_v2.py
"""
import json, re, urllib.request, urllib.parse, ssl

ROOT = r'C:\Users\andys\privacy-yt'
PRODUCT_ID = 'sOap88TaNJAKelU4sjM4IQ=='


def load_token():
    with open(ROOT + r'\.env', encoding='utf-8') as f:
        for line in f:
            if line.startswith('GUMROAD_ACCESS_TOKEN='):
                return line.split('=', 1)[1].strip()
    raise SystemExit('token not found')


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


def md_to_html(md, is_el=False):
    """Μετατρέπει το κείμενο σε HTML για το Gumroad."""
    out = []
    lines = md.split('\n')
    in_ul = False
    for ln in lines:
        s = ln.rstrip()
        if s.strip() == '':                      # κενή
            if in_ul:
                out.append('</ul>')
                in_ul = False
            continue
        if s.strip() == '───────────────────────────────────────────':
            if in_ul:
                out.append('</ul>'); in_ul = False
            out.append('<hr>')
            continue
        if s.startswith('• '):                   # bullet
            if not in_ul:
                out.append('<ul>'); in_ul = True
            out.append('<li>' + s[2:].strip() + '</li>')
            continue
        # Διαχωριστικά αγγλικά (κόβονται στη μέση λέξης; όχι)
        if s.strip() in ('WHAT IT DOES', 'WHAT IT DOESN\'T DO', 'WHAT YOU GET',
                         'REQUIREMENTS', 'ONE CLARIFICATION', 'WHO IT\'S FOR',
                         'BUILD YOUR OWN VERSION OF A CHANNEL'):
            if in_ul:
                out.append('</ul>'); in_ul = False
            out.append('<h3>' + s.strip() + '</h3>')
            continue
        if s.strip() in ('ΤΙ ΚΑΝΕΙ', 'ΤΙ ΔΕΝ ΚΑΝΕΙ', 'ΤΙ ΠΑΙΡΝΕΙΣ',
                         'ΑΠΑΙΤΗΣΕΙΣ', 'ΜΙΑ ΔΙΕΥΚΡΙΝΙΣΗ', 'ΓΙΑ ΠΟΙΟΥΣ ΕΙΝΑΙ',
                         'ΦΤΙΑΞΕ ΤΗ ΔΙΚΗ ΣΟΥ ΒΕΡΣΙΟΝ ΕΝΟΣ ΚΑΝΑΛΙΟΥ'):
            if in_ul:
                out.append('</ul>'); in_ul = False
            out.append('<h3>' + s.strip() + '</h3>')
            continue
        # Headline (κεφαλαία)
        if s.strip().isupper() and len(s.strip()) > 12:
            if in_ul:
                out.append('</ul>'); in_ul = False
            out.append('<p><strong>' + s.strip() + '</strong></p>')
            continue
        # Warn block
        if s.startswith('⚠️'):
            if in_ul:
                out.append('</ul>'); in_ul = False
            out.append('<p><strong>' + s.strip() + '</strong></p>')
            continue
        # Κανονικό κείμενο
        if in_ul:
            out.append('</ul>'); in_ul = False
        out.append('<p>' + s.strip() + '</p>')
    if in_ul:
        out.append('</ul>')
    return '\n'.join(out)


def main():
    md = open(ROOT + r'\legal\COPY-v2.md', encoding='utf-8').read()
    blocks = re.findall(r'```\n(.*?)\n```', md, re.S)
    EN_RAW, EL_RAW = blocks[0].strip(), blocks[1].strip()

    en_html = md_to_html(EN_RAW)
    el_html = md_to_html(EL_RAW, is_el=True)
    DESC = en_html + '\n<hr>\n<h2>🇬🇷 ΕΛΛΗΝΙΚΑ</h2>\n' + el_html

    # Έλεγχοι
    print('Έλεγχοι πριν το ανέβασμα:')
    print('  EN:', 'DIGITAL PRODUCT' in DESC)
    print('  EL:', 'ΑΓΟΡΑ ΨΗΦΙΑΚΟΥ' in DESC)
    print('  html tags:', DESC.count('<p>') + DESC.count('<li>'), 'blocks')
    print('  μέγεθος:', len(DESC))
    print()

    data = {'description': DESC, 'refund_period': '14'}
    st, d = api('https://api.gumroad.com/v2/products/' + urllib.parse.quote(PRODUCT_ID, safe=''),
                method='PUT', data=data)
    print('HTTP', st)
    if d.get('success'):
        p = d['product']
        print('✅ ΑΝΕΒΗΚΕ')
        print('   published    :', p.get('published'))
        print('   refund_policy:', json.dumps(p.get('refund_policy'), ensure_ascii=False))
        print('   desc len     :', len(p.get('description') or ''))
    else:
        print('⚠️', json.dumps(d, ensure_ascii=False)[:400])


if __name__ == '__main__':
    main()