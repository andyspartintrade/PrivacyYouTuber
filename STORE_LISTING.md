# Chrome Web Store — Listing & Υποβολή

Όλα τα κείμενα παρακάτω είναι **έτοιμα για copy-paste**. (Αγγλικά για ευρύτερο κοινό —
μπορείς να προσθέσεις και ελληνική μετάφραση στο dev console αν θες.)

---

## 1. Short description (μέχρι 132 χαρακτήρες)

```
Private YouTube recommendations. Logs what you watch locally — nothing leaves your machine.
```

## 2. Detailed description (copy-paste στο "Detailed description")

```
Privacy YouTuber gives you YouTube recommendations without giving Google your data.

HOW IT WORKS
• Watch YouTube as usual — in Incognito or not.
• The extension logs the videos you watch (title, channel, tags) LOCALLY.
• A local algorithm (TF-IDF, running on your own machine) learns your topics.
• It suggests fresh search queries so you keep discovering new videos.

WHAT MAKES IT PRIVATE
• Your watch history NEVER leaves your computer.
• No account, no login, no cloud, no analytics, no ads.
• The only external call is Google's anonymous autocomplete endpoint, which
  receives a single keyword — not your identity, not your history.

WHAT YOU NEED
• The Privacy YouTuber desktop app (free). The extension is the "sensor";
  the app is the "brain". Download it from the project page, run it, and the
  extension stores everything locally on your machine.

YOUR DATA STAYS YOURS
Everything is stored in a local SQLite database. Delete the app and the data
goes with it. Google learns nothing about what you watch.
```

## 3. Category

**Productivity** (ή "Tools").

## 4. Privacy practices (η Google ρωτάει δομημένα — απάντησε έτσι)

| Ερώτηση | Απάντηση |
|---|---|
| Τι δεδομένα συλλέγει; | **Website content** (τίτλος/κανάλι/tags των βίντεο που βλέπεις) |
| Πού αποθηκεύονται; | **Τοπικά μόνο** — στη βάση της desktop εφαρμογής μέσω localhost |
| Πωλούνται δεδομένα; | **Όχι** |
| Μεταφέρονται σε τρίτους; | **Όχι** |
| Χρησιμοποιούνται για διαφήμιση; | **Όχι** |
| Remote code (απομακρυσμένος κώδικας); | **Κανένας** |

**Single purpose** (η νέα ερώτηση της Google): "Helps users get private, local
YouTube recommendations without sharing their watch history with Google."

## 5. Αιτιολόγηση permission (για το `host_permissions` στο localhost)

```
The extension communicates ONLY with the local companion app at
http://127.0.0.1:8765 to store your watch history on your own machine.
No data is sent over the internet.
```

---

## 6. Screenshots (προαιρετικά αλλά συνιστώνται)

Απαιτούνται **1280×800** (ή 640×400). Πάρε screenshot από το dashboard:
1. Τρέξε `python cli.py serve --open` (ή το `.exe`).
2. Πάρε screenshot τη σελίδα http://localhost:8765.
3. Θόλωσε/αφαίρεσε προσωπικά δεδομένα αν φαίνονται (τίτλοι βίντεο).

## 7. Βήματα υποβολής (checklist)

1. [ ] Δημιούργησε developer account: **https://chrome.google.com/webstore/devconsole**
2. [ ] Πλήρωσε το εφάπαξ **$5** (registration fee).
3. [ ] Κάνε `.zip` τον φάκελο `extension/` (ΠΡΟΣΟΧΗ: το zip να περιέχει τα αρχεία *απευθείας*,
       όχι μέσα σε υποφάκελο).
4. [ ] **Add new item** → ανέβασε το zip.
5. [ ] Συμπλήρωσε description, category, privacy (από πάνω).
6. [ ] Ανεβάζεις screenshots.
7. [ ] **Submit for review** → περιμένεις 1-3 μέρες.

---

## 📦 Πώς κάνεις το zip σωστά

Στον φάκελο `extension/`, επίλεξε ΟΛΑ τα αρχεία (manifest.json, content.js,
popup.html, popup.js, icons/) και κάνε zip. Το zip πρέπει να έχει **στην ρίζα** το
`manifest.json` — όχι έναν φάκελο που το περιέχει.

```
PrivacyYouTuber.zip
├── manifest.json
├── content.js
├── popup.html
├── popup.js
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```
