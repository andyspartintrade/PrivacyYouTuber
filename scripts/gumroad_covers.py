"""Ανεβάζει τα screenshots ως covers στο Gumroad (POST /products/:id/covers).
Τα URLs είναι από GitHub raw (public).
"""
import os, json, urllib.request, urllib.parse, time
from dotenv import load_dotenv

load_dotenv()
TOK = os.environ.get('GUMROAD_ACCESS_TOKEN', '')
PID = os.environ.get('GUMROAD_PRODUCT_ID', 'sOap88TaNJAKelU4sjM4IQ==')
BASE = 'https://raw.githubusercontent.com/andyspartintrade/PrivacyYouTuber/main/gumroad-screenshots'

# Η σειρά που θα δείχνονται (marketing flow)
SHOTS = [
    '01-search-results.png',
    '02-find-channels.png',
    '04-recent-searches.png',
    '06-your-channels.png',
    '07-categories.png',
    '10-category-popup.png',
    '08-player-notes.png',
    '09-settings.png',
    '03-any-video.png',
    '05-your-tags.png',
]

print(f'=== ΑΝΕΒΑΣΜΑ {len(SHOTS)} COVERS ===')
ok = 0
for i, name in enumerate(SHOTS, 1):
    url = f'{BASE}/{name}'
    body = urllib.parse.urlencode({'access_token': TOK, 'url': url}).encode()
    req = urllib.request.Request(
        f'https://api.gumroad.com/v2/products/{PID}/covers',
        data=body, method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=90)
        d = json.load(r)
        print(f'  [{i:2d}] {name:26s} → success={d.get("success")}')
        ok += 1
    except urllib.error.HTTPError as e:
        print(f'  [{i:2d}] {name:26s} → HTTP {e.code}: {e.read().decode()[:120]}')
    except Exception as e:
        print(f'  [{i:2d}] {name:26s} → ERR {str(e)[:80]}')
    time.sleep(1)

print(f'\nΑνέβηκαν: {ok}/{len(SHOTS)}')

# ── ΕΠΑΛΗΘΕΥΣΗ ──
print('\n=== ΕΠΑΛΗΘΕΥΣΗ (τι βλέπει το API) ===')
req = urllib.request.Request(
    f'https://api.gumroad.com/v2/products/{PID}',
    headers={'Authorization': 'Bearer ' + TOK})
d = json.load(urllib.request.urlopen(req, timeout=30))
p = d.get('product', {})
covers = p.get('covers') or []
print(f'  covers: {len(covers)}')
for c in covers:
    print(f'    - id={c.get("id")} | {str(c.get("url"))[:70]}')
print(f'  main_cover_id: {p.get("main_cover_id")}')
