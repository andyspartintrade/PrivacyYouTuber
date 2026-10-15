"""Ανεβάζει το YouTube βίντεο ως FIRST cover + τα 7 screenshots με σωστή σειρά.
1. Διαγράφει όλα τα covers
2. Βάζει YouTube video ΠΡΩΤΟ
3. Ξαναβάζει τα σωστά screenshots
"""
import os, json, urllib.request, urllib.parse, time
from dotenv import load_dotenv

load_dotenv()
TOK = os.environ.get('GUMROAD_ACCESS_TOKEN', '')
PID = 'sOap88TaNJAKelU4sjM4IQ=='
API = f'https://api.gumroad.com/v2/products/{PID}'
BASE = 'https://raw.githubusercontent.com/andyspartintrade/PrivacyYouTuber/main/gumroad-screenshots'
YT = 'https://www.youtube.com/watch?v=uK3zPFE9-AU'

# ΣΩΣΤΗ ΣΕΙΡΑ: YouTube πρώτο, μετά τα screenshots
ORDER = [
    ('yt',  YT),                                    # 1. ΤΟ ΒΙΝΤΕΟ ⭐
    ('img', f'{BASE}/01-search-results.png'),       # 2. Search results
    ('img', f'{BASE}/02-find-channels.png'),        # 3. Find channels
    ('img', f'{BASE}/04-recent-searches.png'),      # 4. Recent searches
    ('img', f'{BASE}/06-your-channels.png'),        # 5. Your channels
    ('img', f'{BASE}/07-categories.png'),           # 6. Categories
    ('img', f'{BASE}/10-category-popup.png'),       # 7. Category popup
    ('img', f'{BASE}/08-player-notes.png'),         # 8. Player + Notes
    ('img', f'{BASE}/09-settings-EN.png'),          # 9. Settings
]

def get_product():
    req = urllib.request.Request(API, headers={'Authorization': 'Bearer ' + TOK})
    return json.load(urllib.request.urlopen(req, timeout=30)).get('product', {})

# 1. ΔΙΑΓΡΑΦΗ ΟΛΩΝ
p = get_product()
covers = p.get('covers') or []
print(f'=== ΔΙΑΓΡΑΦΗ {len(covers)} covers ===')
for c in covers:
    body = urllib.parse.urlencode({'access_token': TOK}).encode()
    req = urllib.request.Request(f'{API}/covers/{c["id"]}', data=body, method='DELETE')
    try:
        urllib.request.urlopen(req, timeout=60)
        print(f'  ✅ {c["id"][:16]}...')
    except Exception as e:
        print(f'  ❌ {str(e)[:50]}')
    time.sleep(1)

# 2. ΞΑΝΑΒΑΖΩ ΜΕ ΣΕΙΡΑ
print(f'\n=== ΞΑΝΑΒΑΖΩ {len(ORDER)} covers (YouTube ΠΡΩΤΟ) ===')
for i, (kind, url) in enumerate(ORDER, 1):
    body = urllib.parse.urlencode({'access_token': TOK, 'url': url}).encode()
    req = urllib.request.Request(f'{API}/covers', data=body, method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=90)
        d = json.load(r)
        label = 'YT VIDEO' if kind == 'yt' else url.split('/')[-1]
        print(f'  {i}. [{label}] success={d.get("success")}')
    except urllib.error.HTTPError as e:
        print(f'  {i}. HTTP {e.code}: {e.read().decode()[:100]}')
    time.sleep(2)

# 3. ΕΠΑΛΗΘΕΥΣΗ
print('\n=== ΤΕΛΙΚΗ ΣΕΙΡΑ ===')
p2 = get_product()
c2 = p2.get('covers') or []
for i, c in enumerate(c2, 1):
    main = ' ⭐ ΚΥΡΙΟ' if c.get('id') == p2.get('main_cover_id') else ''
    print(f'  {i}. {c.get("id")[:16]}...{main}')
print(f'\n  main_cover_id: {p2.get("main_cover_id")}')
print(f'  published: {p2.get("published")}')
