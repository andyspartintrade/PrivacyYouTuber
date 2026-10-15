"""Αντικαθιστά το ΕΛΛΗΝΙΚΟ settings cover με το ΑΓΓΛΙΚΟ.
1. Βρίσκει ποιο cover είναι το settings (το 8ο που ανέβηκε — 84261703...)
2. DELETE αυτό
3. POST το νέο αγγλικό
"""
import os, json, urllib.request, urllib.parse, time
from dotenv import load_dotenv

load_dotenv()
TOK = os.environ.get('GUMROAD_ACCESS_TOKEN', '')
PID = 'sOap88TaNJAKelU4sjM4IQ=='
API = f'https://api.gumroad.com/v2/products/{PID}'

def get_product():
    req = urllib.request.Request(API, headers={'Authorization': 'Bearer ' + TOK})
    return json.load(urllib.request.urlopen(req, timeout=30)).get('product', {})

p = get_product()
covers = p.get('covers') or []
print(f'=== ΠΡΙΝ: {len(covers)} covers ===')
for i, c in enumerate(covers, 1):
    print(f'  {i}. {c.get("id")[:20]}...')

# Το settings ήταν το 8ο (τελευταίο που ανέβηκε 성공)
# Σύμφωνα με τη σειρά upload: 08-player-notes ήταν 7ο, 09-settings 8ο
target = None
if len(covers) >= 8:
    target = covers[7].get('id')   # το 8ο = settings (ελληνικό)
print(f'\n=== ΘΑ ΣΒΗΣΩ: {target} ===')

if target:
    body = urllib.parse.urlencode({'access_token': TOK}).encode()
    req = urllib.request.Request(f'{API}/covers/{target}', data=body, method='DELETE')
    try:
        r = urllib.request.urlopen(req, timeout=60)
        d = json.load(r)
        print(f'  DELETE: success={d.get("success")}')
    except urllib.error.HTTPError as e:
        print(f'  DELETE HTTP {e.code}: {e.read().decode()[:200]}')
    time.sleep(2)

# POST το νέο αγγλικό
url = 'https://raw.githubusercontent.com/andyspartintrade/PrivacyYouTuber/main/gumroad-screenshots/09-settings-EN.png'
body = urllib.parse.urlencode({'access_token': TOK, 'url': url}).encode()
req = urllib.request.Request(f'{API}/covers', data=body, method='POST')
try:
    r = urllib.request.urlopen(req, timeout=90)
    d = json.load(r)
    print(f'  POST νέο: success={d.get("success")} | id={d.get("cover",{}).get("id")}')
except urllib.error.HTTPError as e:
    print(f'  POST HTTP {e.code}: {e.read().decode()[:200]}')

# ── ΤΕΛΙΚΟ ──
p2 = get_product()
c2 = p2.get('covers') or []
print(f'\n=== ΜΕΤΑ: {len(c2)} covers ===')
for i, c in enumerate(c2, 1):
    print(f'  {i}. {c.get("id")[:20]}... | {str(c.get("original_url",""))[:60]}')
print(f'  main: {p2.get("main_cover_id")}')
