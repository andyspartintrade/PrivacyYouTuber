# 🔒 Privacy-YouTuber — Privacy-First Recommendation System (MVP)

Ένα τοπικό σύστημα προτάσεων για το YouTube, **χωρίς να δίνεις δεδομένα στη Google**.

Βλέπεις βίντεο σε **Incognito** → το εργαλείο καταγράφει **τοπικά** (SQLite) τα θέματα που
παρακολουθείς → ένας **τοπικός αλγόριθμος** σου προτείνει νέα θέματα προς αναζήτηση.

**Τίποτα από το ιστορικό σου δεν φεύγει από το μηχάνημά σου.**

---

## 🧠 Η φιλοσοφία (τι μένει μέσα, τι βγαίνει έξω)

| Τι γίνεται | Πού | Τι μαθαίνει η Google |
|---|---|---|
| Καταγραφή του τι βλέπεις | **Τοπικά** (SQLite) | Τίποτα |
| Εξαγωγή θεμάτων | **Τοπικά** (TF-IDF) | Τίποτα |
| Ανώνυμες προτάσεις αναζήτησης | Google `suggestqueries` | **Μόνο μία λέξη-κλειδί**, χωρίς cookie/ταυτότητα |

Η μόνη εξωτερική κλήση είναι το endpoint αυτόματης συμπλήρωσης της Google
(`suggestqueries.google.com`), που δέχεται **ένα σκέτο query string** — όχι το ιστορικό σου,
όχι το ποιος είσαι. Είναι σαν να ρωτάς έναν ξένο στον δρόμο «τι ώρα είναι»: αυτός δεν
μαθαίνει το όνομά σου.

---

## 📁 Δομή αρχείων

```
privacy-yt/
├── README.md                 ← αυτό το αρχείο
├── cli.py                    ← το κεντρικό CLI (serve / stats / recommend)
├── server/
│   ├── __init__.py
│   ├── app.py                ← τοπικός HTTP server (Python stdlib, μηδέν deps)
│   ├── db.py                 ← σχήμα SQLite + βοηθητικές συναρτήσεις
│   └── recommender.py        ← τοπικός αλγόριθμος TF-IDF + προτάσεις
├── extension/
│   ├── manifest.json         ← Manifest V3
│   └── content.js            ← πιάνει το metadata και το στέλνει στο localhost
└── data/
    └── privacy_yt.db         ← η βάση (δημιουργείται μόνη της)
```

---

## 🚀 Εγκατάσταση (βήμα-βήμα)

### 1. Απαιτήσεις
Μόνο **Python 3.9+** (την έχεις ήδη). **Κανένα pip install** — όλα τα imports είναι stdlib.

### 2. Φόρτωσε το extension στον browser (Brave / Chrome)
1. Άνοιξε `brave://extensions` (ή `chrome://extensions`).
2. Ενεργοποίησε το **Developer mode** (δεξιά πάνω).
3. Πάτησε **Load unpacked** και διάλεξε τον φάκελο `privacy-yt/extension`.
4. Τέλος! Το extension τρέχει μόνο στο `www.youtube.com` και στέλνει μόνο στο `127.0.0.1`.

### 3. Ξεκίνα τον τοπικό server
```bash
cd privacy-yt
python cli.py serve
```
Θα δεις:
```
Listening on http://127.0.0.1:8765
```

### 4. Δες τι έχεις καταγράψει
Άνοιξε **δεύτερο terminal**:
```bash
python cli.py stats
```

### 5. Πάρε προτάσεις
```bash
python cli.py recommend
```
Θα δεις:
- 🎯 **Τα θέματα που σε ενδιαφέρουν** (βγαλμένα τοπικά από το ιστορικό σου)
- 🔎 **Ανώνυμες προτάσεις αναζήτησης** για να τις κάνεις copy-paste στο YouTube Incognito.

---

## 📥 Εισαγωγή του ιστορικού που ήδη έχεις (Google Takeout)

Αντί να ξεκινάς από το μηδέν, μπορείς να τραβήξεις ΟΛΟ το υπάρχον ιστορικό σου
— με τον πιο privacy-friendly, επίσημο τρόπο:

1. Πήγαινε στο **https://takeout.google.com**.
2. Διάλεξε ΜΟΝΟ το **YouTube and YouTube Music**.
3. Πάτησε **Multiple formats** → στο **History** διάλεξε **JSON** (όχι HTML).
4. Πάτησε **Next step** → **Create export** → κατέβασε το αρχείο.
5. Αποσυμπίεσε το `.zip` σε έναν φάκελο (π.χ. `C:\Users\andys\Takeout`).
6. Τρέξε:
   ```bash
   python cli.py import "C:\Users\andys\Takeout"
   ```

Το script βρίσκει μόνο του το `watch-history.json` (όσο βαθιά κι αν είναι), εισάγει
τα βίντεο με τα **πραγματικά τους timestamps**, συγχωνεύει τα διπλότυπα, και σου
δείχνει και πόσες **συνδρομές** έχεις.

💡 **Μπόνους:** αφού κάνεις το export, μπορείς να **διαγράψεις το ιστορικό σου από τη
Google** (myactivity.google.com). Τα δεδομένα σου θα ζουν πλέον μόνο τοπικά.

---

## ⚙️ Πώς δουλεύει ο αλγόριθμος (απλά)

**TF-IDF** (Term Frequency — Inverse Document Frequency):
- Κάθε βίντεο γίνεται ένα «σάκο από λέξεις» (τίτλος + tags + κατηγορία).
- Σπάνιες λέξεις (π.χ. «φωτοβολταϊκά», «stealth») παίρνουν μεγαλύτερο βάρος από συχνές («το», «και»).
- Το «προφίλ» σου = το άθροισμα όλων των βίντεο που είδες, ζυγισμένο με το πόσες φορές τα είδες.
- Οι κορυφαίες λέξεις του προφίλ = **τα θέματά σου**.

Καμία αποστολή σε cloud. Όλα μέσα στο `recommender.py`, καθαρό Python.

---

## 📦 Διανομή σαν εγκαταστάσιμη εφαρμογή

Ο τελικός χρήστης **δεν χρειάζεται Python**. Η εφαρμογή έχει δύο κομμάτια που
εγκαθίστανται ξεχωριστά:

### 1. Το desktop app (server + AI) → ένα `.exe`
```bash
python build_exe.py
```
Φτιάχνει `dist/PrivacyYouTuber.exe` (PyInstaller, one-file). Ο χρήστης το κάνει
**διπλό κλικ** → ξεκινά ο server και ανοίγει αυτόματα το **dashboard** στον browser
(http://localhost:8765). Τα δεδομένα αποθηκεύονται στο `%LOCALAPPDATA%\PrivacyYouTuber`.

Προαιρετικά, για «σωστό» installer με start menu + αυτόματη εκκίνηση:
άνοιξε το `installer/PrivacyYouTuber.iss` με το **Inno Setup** και πάτα Compile.

### 2. Το browser extension → Chrome Web Store
1. Πήγαινε στο **https://chrome.google.com/webstore/devconsole**.
2. Πλήρωσε το εφάπαξ **$5** developer fee.
3. Ανεβάζεις τον φάκελο `extension/` (κάν' τον `.zip`).
4. Περιμένεις την έγκριση (συνήθως 1-3 μέρες).

> Εναλλακτικά, δωρεάν & άμεσα: στέλνεις στον χρήστη τον φάκελο `extension/` ως `.zip`
> και του λες «brave://extensions → Developer mode → Load unpacked».

### Το dashboard (web UI)
Όταν τρέχει η εφαρμογή, ανοίγει μια τοπική σελίδα με: 📊 στατιστικά, 🎯 τα θέματά σου,
🔎 **κλικάρισμα** προτάσεις αναζήτησης (ανοίγουν YouTube σε νέο tab), 📚 τη βιβλιοθήκη σου.
Όλα στο `web/index.html` — μηδέν εξωτερικά CDN, μηδέν tracking.

---

## 🗺️ Επόμενα βήματα (Phase 2 — εκτός MVP)

- **Νέα βίντεο, όχι μόνο νέα θέματα:** scraping αποτελεσμάτων YouTube με `yt-dlp` (ανώνυμα).
- **Τοπικά embeddings:** αντί για TF-IDF, χρησιμοποίησε τοπικό LLM (π.χ. Gemma) για semantic
  similarity — ήδη έχεις το hardware και το LM Studio.
- **Κουμπί «δεν μου αρέσει»:** το extension στέλνει και αρνητικό feedback στο ίδιο endpoint.
- **Web UI** αντί για CLI, αν θες να βλέπεις τα πάντα σε μια σελίδα.
