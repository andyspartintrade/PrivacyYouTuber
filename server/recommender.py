"""Τοπικός recommender — καθαρό Python TF-IDF, μηδέν εξαρτήσεις.

Ροή:
  1. Φορτώνει τα βίντεο από τη βάση.
  2. Χτίζει ένα «προφίλ θεμάτων» (ζυγισμένο TF-IDF, με βάση και το watch_count).
  3. Τυπώνει τα κορυφαία θέματα.
  4. Για κάθε θέμα, ρωτάει το (ανώνυμο) suggest endpoint της Google και δίνει
     έτοιμες προτάσεις αναζήτησης για copy-paste στο YouTube Incognito.

Σημείωση privacy: το suggestqueries δέχεται ΜΟΝΟ το query string — δεν στέλνουμε
cookie, ιστορικό ή ταυτότητα. Η Google δεν μαθαίνει τίποτα για σένα.
"""

import json
import math
import re
import urllib.parse
import urllib.request
from collections import Counter

# Stopwords ελληνικά + αγγλικά — οι «θόρυβοι» που δεν σημαίνουν τίποτα.
_GREEK_STOP = set(
    """και το η ο τα του της των στη στον στους στις για με σε από να δεν που
    είναι ότι αυτό αυτή αυτός είμαι είσαι ένα μια πολύ όταν τι πως όλα όλοι
    θα μετά αλλά σαν ή όμως έτσι γιατί ακόμα μόνο άλλο άλλα εδώ εκεί""".split()
)
_ENG_STOP = set(
    """the a an and or of to in on for with at by is are was were be been this
    that these those it its i you he she we they as if then than so not no do
    does did have has had what how why when who which your my our their""".split()
)
STOP = _GREEK_STOP | _ENG_STOP


def tokenize(text):
    """Σπάει κείμενο σε λέξεις, πετάει stopwords και μονογράμματα."""
    text = (text or "").lower()
    # [^\W_] = «γράμμα ή ψηφίο» (unicode, πιάνει και τονισμένα ελληνικά) χωρίς το _.
    words = re.findall(r"[^\W_]{2,}", text, re.UNICODE)
    return [w for w in words if w not in STOP]


def _video_text(v):
    tags = " ".join(json.loads(v.get("tags") or "[]"))
    return " ".join([v.get("title", ""), v.get("category") or "", tags])


def _build_docs(videos):
    return [tokenize(_video_text(v)) for v in videos]


def _document_frequency(docs):
    df = Counter()
    for d in docs:
        for t in set(d):
            df[t] += 1
    return df


def _tfidf(doc, df, n_docs):
    tf = Counter(doc)
    vec = {}
    for term, freq in tf.items():
        idf = math.log((n_docs + 1) / (df[term] + 1)) + 1.0
        vec[term] = (1.0 + math.log(freq)) * idf
    return vec


def top_terms(videos, n=8):
    """Επιστρέφει τις n πιο χαρακτηριστικές λέξεις του προφίλ σου."""
    docs = _build_docs(videos)
    n_docs = len(docs)
    df = _document_frequency(docs)
    profile = Counter()
    for v, doc in zip(videos, docs):
        vec = _tfidf(doc, df, n_docs)
        # Βάρος: προβολές × (κατάταξη) × (pin).
        # Τα ψηλά/pinned βίντεο βαραίνουν περισσότερο → η αναζήτηση έρχεται πιο κοντά
        # στα αγαπημένα σου.
        weight = (
            v.get("watch_count", 1)
            * (1.0 + 0.3 * (v.get("rank") or 0) + (3.0 if v.get("pinned") else 0.0))
        )
        for term, val in vec.items():
            profile[term] += val * weight
    return [t for t, _ in profile.most_common(n)]


def fetch_suggestions(query, hl="el", limit=4):
    """Ανώνυμες προτάσεις αυτόματης συμπλήρωσης της Google (YouTube)."""
    url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
        {"client": "youtube", "ds": "yt", "q": query, "hl": hl}
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (privacy-yt; local)"}
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        raw = resp.read().decode("utf-8", "ignore")
    # Η απάντηση είναι JSONP: window.google.ac.h([...]); — βγάλε το wrapper.
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return []
    data = json.loads(m.group(0))
    # Δομή: [query, [[κείμενο, 0, [512]], ...]] → κράτα μόνο το κείμενο.
    if len(data) < 2:
        return []
    return [item[0] for item in data[1]][:limit]


def recommend(videos, top_n=5):
    terms = top_terms(videos, n=8)

    print("🎯 Θέματα που σε ενδιαφέρουν (βγαλμένα τοπικά από το ιστορικό σου):")
    for t in terms:
        print(f"   • {t}")
    print()

    print("🔎 Δοκίμασε αυτές τις αναζητήσεις στο YouTube (Incognito):")
    any_sugg = False
    for t in terms[:top_n]:
        try:
            suggs = fetch_suggestions(t)
            if suggs:
                any_sugg = True
                for s in suggs:
                    print(f"   • {s}")
        except Exception as exc:  # no internet, ή η Google απάντησε αλλιώς
            print(f"   • (δεν βρήκα προτάσεις για «{t}» — {exc})")
    if not any_sugg:
        print("   (καμία πρόταση — τσέκαρε τη σύνδεση δικτύου)")
