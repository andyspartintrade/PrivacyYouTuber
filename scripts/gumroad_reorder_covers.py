"""Ξαναβάζει τα covers με τη ΣΩΣΤΗ σειρά (Settings τελευταίο).
1. Διαγράφει όλα τα υπάρχοντα covers
2. Ξαναβάζει με τη σειρά που θέλει ο χρήστης — το πρώτο γίνεται κύριο
"""
import os, json, urllib.request, urllib.parse, time
from dotenv import load_dotenv

load_dotenv()
TOK = os.environ.get('GUMROAD_ACCESS_TOKEN', '')
PID = 'sOap88TaNJAKelU4sjM4IQ=='
API = f'https://api.gumroad.com/v2/products/{PID}'
BASE = 'https://raw.githubusercontent.com/andyspartintrade/PrivacyYouTuber/main/gumroad-screenshots'

# Η ΣΕΙΡΑ που θέλει ο χρήστης (πρώτο = κύριο)
ORDER = [
    '01-search-results.png',
    '02-find-channels.png',
    '04-recent-searches.png',
    '06-your-channels.png',
    '07-categories.png',
    '10-category-popup.png',
    '08-player-notes.png',
    '09-settings-EN.png',
]

def get_product():
    req = urllib.request.Request(API, headers={'Authorization': 'Bearer ' + TOK})
    return json.load(urllib.request.urlopen(req, timeout=30)).get('product', {})

# ── 1. ΔΙΑΓΡΑΦΗ ΟΛΩΝ ──
p = get_product()
covers = p.get('covers') or []
print(f'=== ΔΙΑΓΡΑΦΗ {len(covers)} covers ===')
for c in covers:
    cid = c.get('id')
    body = urllib.parse.urlencode({'access_token': TOK}).encode()
    req = urllib.request.Request(f'{API}/covers/{cid}', data=body, method='DELETE')
    try:
        r = urllib.request.urlopen(req, timeout=60)
        d = json.load(r)
        print(f'  [{cid[:16]}...] DELETE success={d.get("success")}')
    except urllib.error.HTTPError as e:
        print(f'  [{cid[:16]}...] HTTP {e.code}')
    time.sleep(1)

# ── 2. ΞΑΝΑΒΑΖΩ ΜΕ ΣΕΙΡΑ ──
print(f'\n=== ΞΑΝΑΒΑΖΩ {len(ORDER)} covers ===')
for i, name in enumerate(ORDER, 1):
    body = urllib.parse.urlencode({'access_token': TOK, 'url': f'{BASE}/{name}'}).encode()
    req = urllib.request.Request(f'{API}/covers', data=body, method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=90)
        d = json.load(r)
        print(f'  {i}. {name:26s} → success={d.get("success")}')
    except urllib.error.HTTPError as e:
        print(f'  {i}. {name:26s} → HTTP {e.code}')
    time.sleep(2)

# ── 3. ΕΠΑΛΗΘΕΥΣΗ ──
print('\n=== ΤΕΛΙΚΗ ΣΕΙΡΑ ===')
p2 = get_product()
c2 = p2.get('covers') or []
for i, c in enumerate(c2, 1):
    main = ' ⭐ ΚΥΡΙΟ' if c.get('id') == p2.get('main_cover_id') else ''
    print(f'  {i}. {c.get("id")[:20]}...{main}')
print(f'\n  main_cover_id: {p2.get("main_cover_id")}')
print(f'  published:     {p2.get("published")}')
