"""ΤΕΛΙΚΗ σειρά covers: YouTube video ΠΡΩΤΟ + 8 screenshots.
Αφαιρεί το αδιάφορο dropdown (6eb63dc6).
"""
import os, json, urllib.request, urllib.parse, time
from dotenv import load_dotenv

load_dotenv()
TOK = os.environ.get('GUMROAD_ACCESS_TOKEN', '')
PID = 'sOap88TaNJAKelU4sjM4IQ=='
API = f'https://api.gumroad.com/v2/products/{PID}'
BASE = 'https://raw.githubusercontent.com/andyspartintrade/PrivacyYouTuber/main/gumroad-screenshots'
YT = 'https://www.youtube.com/watch?v=uK3zPFE9-AU'

ORDER = [
    ('YT VIDEO',                YT),
    ('Search results',          f'{BASE}/01-search-results.png'),
    ('Find channels',           f'{BASE}/02-find-channels.png'),
    ('Recent searches',         f'{BASE}/04-recent-searches.png'),
    ('Your channels',           f'{BASE}/06-your-channels.png'),
    ('Categories',              f'{BASE}/07-categories.png'),
    ('Category popup',          f'{BASE}/10-category-popup.png'),
    ('Player + Notes',          f'{BASE}/08-player-notes.png'),
    ('Settings (EN)',           f'{BASE}/09-settings-EN.png'),
]

def get_product():
    req = urllib.request.Request(API, headers={'Authorization': 'Bearer ' + TOK})
    return json.load(urllib.request.urlopen(req, timeout=30)).get('product', {})

p = get_product()
covers = p.get('covers') or []
print(f'=== ΔΙΑΓΡΑΦΗ {len(covers)} ===')
for c in covers:
    body = urllib.parse.urlencode({'access_token': TOK}).encode()
    req = urllib.request.Request(f'{API}/covers/{c["id"]}', data=body, method='DELETE')
    try:
        urllib.request.urlopen(req, timeout=60)
        print(f'  ✅ {c["id"][:14]}...')
    except Exception as e:
        print(f'  ❌ {str(e)[:45]}')
    time.sleep(1)

print(f'\n=== ΞΑΝΑΒΑΖΩ {len(ORDER)} (YouTube #1) ===')
for i, (label, url) in enumerate(ORDER, 1):
    body = urllib.parse.urlencode({'access_token': TOK, 'url': url}).encode()
    req = urllib.request.Request(f'{API}/covers', data=body, method='POST')
    try:
        d = json.load(urllib.request.urlopen(req, timeout=90))
        print(f'  {i}. {label:20s} success={d.get("success")}')
    except urllib.error.HTTPError as e:
        print(f'  {i}. {label:20s} HTTP {e.code}')
    time.sleep(2)

print('\n=== ΤΕΛΙΚΟ ===')
p2 = get_product()
c2 = p2.get('covers') or []
for i, c in enumerate(c2, 1):
    m = ' ⭐ ΚΥΡΙΟ' if c.get('id') == p2.get('main_cover_id') else ''
    print(f'  {i}. {c.get("id")[:14]}...{m}')
print(f'\n  main_cover_id: {p2.get("main_cover_id")}')
print(f'  published: {p2.get("published")}')
