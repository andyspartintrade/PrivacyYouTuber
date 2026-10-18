# ΕΠΟΜΕΝΗ ΣΥΝΕΔΡΙΑ — PrivacyYouTuber

> Τελευταία ενημέρωση: **16/10/2026, 04:45** (τέλος συνεδρίας **v1.4.2**)

---

## ✅ ΤΙ ΟΛΟΚΛΗΡΩΘΗΚΕ ΣΤΗ ΣΥΝΕΔΡΙΑ 16/10 (v1.4.2)

### ΝΟΜΙΚΑ — EULA v1.2 (EN + EL)
1. **EULA v1.2** — 11 άρθρα, **16 Οκτωβρίου 2026** (legal/EULA-EN.md, legal/EULA-EL.md)
   - Α1: Parties & System Requirements (Win 10/11, 64-bit, internet)
   - Α2: License grant — **5 devices**, commercial = ξεχωριστή άδεια, **Οδηγία 2009/24/ΕΚ**
   - Α3: Merchant of Record (Gumroad) + ΦΠΑ + 14 ημέρες + key deactivation σε refund
   - Α4: «AS IS» + third-party dependencies («essential characteristic») + **Οδηγία (EU) 2019/770**
   - Α5: No affiliation + open-source (yt-dlp)
   - Α6: Limitation of liability + εξαιρέσεις (death/fraud/gross negligence)
   - Α7: Personal Data + THIRD-PARTY CONNECTIONS + **GDPR** (Α6(1)(β))
   - Α8: Updates «**at our discretion**» — καμία υποχρέωση συντήρησης
   - Α9: Modifications (χωρίς retroactive μείωση)
   - Α10: Greek law + **CISG exclusion** + Athens courts + **ADR**
   - ΑΦΑΙΡΕΘΗΚΑΝ: υπογραφή Name/Date/License key, «12.00 EUR»
   - ΕΛ: **Ν. 2121/1993**, **Ν. 2251/1994**, ΓΚΠΔ
2. **Αντιπαραβολή EN-EL** — 11/11 άρθρα, ίδια δομή/νούμερα, cross-links σωστά
3. **installer/make_eula.py** — διορθώθηκε ο marker (όχι διπλή γραμμή αποδοχής)
4. **installer/legal/EULA-EN.txt** (232 γρ.) + **EULA-EL.txt** (258 γρ.)

### ΤΕΧΝΙΚΑ
5. **FAIL-OPEN license fix** (κρίσιμο):
   - ΠΡΙΝ: LICENSE_MAX_FAILS = 1 → 2 ανοίγματα offline = κλείδωμα τίμιου πελάτη
   - ΤΩΡΑ: **fail-open ΠΑΝΤΑ** για ενεργοποιημένους
   - **Hard-lock ΜΟΝΟ** σε ρητό flag: refunded / disputed / uses > 5
   - /activate_license παραμένει αυστηρό (σωστό)
6. **Διγλωσσία license errors**: server → **μόνο** error_code (lowercase_key/network/revoked) → frontend MAP + i18n. **293 → 295 keys**
7. **SYNC BUG**: root index.html/i18n.json ήταν **64 γρ.** / **10 keys** πίσω → auto-update θα έστελνε παλιό UI. Backup: backups/root-frontend-OLD-20261016_042031/
8. **OVERRIDE BUG**: %LOCALAPPDATA%\PrivacyYouTuber\web\ (πρώτη προτεραιότητα) ήταν παλιό → ενημερώθηκε. Backup: backups/override-web-OLD-20261016_042335/
9. **VERSION → 1.4.2** παντού

### BUILDS & DELIVERY
10. **App 1.4.2** — dist_onedir/PrivacyYouTuber/ (66 MB, exe 13.036.803 B)
11. **Installer 1.4.2** — dist_onedir/PrivacyYouTuber-Setup-1.4.2.exe (**27.057.489 B**) → **ανέβηκε στο Gumroad από τον χρήστη**
12. **GitHub** (API): legal/EULA-*.md (link **δουλεύει**), index.html+i18n.json+i18n.js (commits 01cd001c2b, 7be3cc3324, d8aa96bd5b)
13. **Gumroad περιγραφή** (API, 200): «1 computer»→«**1 user, up to 5 devices**», «Version 1.x updates»→«**current version, yours to keep**», «Support by email»→«**14-day money-back**», «install themselves»→«**update check**» + ΝΕΟ section «**ONE-TIME PURCHASE — PLEASE READ**» με «**at the developer's discretion**». Backup: backups/gumroad-description-BACKUP.md

### ΑΣΦΑΛΕΙΑ
14. **Token leak audit** — όλα τα artifacts (exe/installer/onefile/Desktop) **ΚΑΘΑΡΑ**
15. **GitHub token** — διορθώθηκε το format, χρησιμοποιήθηκε, **διαγράφηκε**

---

## ΕΚΚΡΕΜΕΙ — ΕΠΟΜΕΝΟ BUILD (v1.4.3)

### #1: ΤΟ LICENSE ΦΕΥΓΕΙ ΜΕ ΤΟ EXPORT
**Πρόβλημα**: το license state ζει στο ui_state (key='license') και το ui_state **περιλαμβάνεται** στο EXPORT_TABLES → το export JSON περιέχει {"activated": true, "license_key": "..."}.

**Συνέπεια**: Export → δώσιμο σε φίλο → Import (replace) → **activated χωρίς key**.

**Απόφαση χρήστη (16/10)**: «δεν κερδίζει κάτι γιατί κινδυνεύει να αποκλειστεί και μπορεί να μας κάνει και λίγη διαφήμιση. Δεν είναι της στιγμής.» → **επόμενο build**.

**Fix** (όταν γίνει, server/db.py):
- export_all() → **εξαίρεση** του row με key='license' (κράτα μόνο key='ui')
- import_all() → **αγνόησε** τυχόν license row (backwards compatible)

### #2: VERSION RESOURCE (cosmetic)
- Το exe **δεν** έχει FileVersion/ProductVersion → Properties→Details κενό
- Fix: version_info.txt + PyInstaller --version-file · Bonus: έκδοση στο Settings UI

### #3: Auto-update chain (όταν μεγαλώσει η βάση πελατών)
- latest.json παραμένει **1.4.0** επίτηδες (1 πελάτης = Μάρθα → χειροκίνητο)
- Όταν χρειαστεί: "version": "1.4.3" + "update_kind": "full" + "download_url" (→ Gumroad)

---

## ΣΗΜΑΝΤΙΚΑ (ΜΑΘΗΜΑΤΑ)

### ΤΟ OVERRIDE ΚΕΡΔΙΖΕΙ ΠΑΝΤΑ
```
Σειρά σερβιρίσματος:
   1. %LOCALAPPDATA%\PrivacyYouTuber\web\index.html   <- OVERRIDE (προτεραιότητα!)
   2. <project>\web\index.html                          <- built-in
```
Οταν αλλάζεις frontend, sync σε 3 σημεία: web/ (πηγή) → root (index.html, i18n.json) → override.

### ΔΥΟ ΒΑΣΕΙΣ — ΔΥΟ ΚΟΣΜΟΙ
| Πώς τρέχει | Βάση |
|---|---|
| **exe** (frozen) | %LOCALAPPDATA%\PrivacyYouTuber\privacy_yt.db <- η κανονική |
| **python cli.py** (dev) | <project>\data\privacy_yt.db <- άδεια δοκιμαστική |

Ο dev server βλέπει ΑΛΛΗ βάση — τα κανάλια του χρήστη δεν είναι εκεί. ΜΗΝ μπερδεύομαι.

### ΠΟΤΕ DELETE ΣΤΟ GUMROAD — ΜΟΝΟ UNPUBLISH
Delete → API error → κλειδώνονται οι υπάρχοντες πελάτες (νομική ευθύνη).

### Ο ΚΑΝΟΝΑΣ NSIS / .txt
- make_eula.py → .txt με UTF-8 + CRLF
- _build_tmp.nsi → **ΜΕ BOM** (encoding="utf-8-sig") — αλλιώς «Bad text encoding» μόνο μετά από Python write
- build_installer.bat → **δεν** δουλεύει από git-bash· κάλεσε τον makensis άμεσα
- **ΜΗΝ τρέχεις headless browsers** — ο χρήστης ζεσταίνεται

### ΤΟ LICENSE ΕΠΙΒΙΩΝΕΙ ΑΠΟ REINSTALL (EULA Α7)
Ζει στη βάση ui_state.key='license' → ο πελάτης δεν ξαναβάζει key μετά από update/uninstall.

---

## ΧΡΗΣΙΜΕΣ ΕΝΤΟΛΕΣ

```bash
# Build onedir (+ Desktop copy, χωρίς .env)
rm -rf dist_onedir build_onedir_work && python build_onedir.py

# EULA .txt (πριν το makensis)
python installer/make_eula.py

# Installer (BOM-safe): γράψε πρώτα το _build_tmp.nsi με utf-8-sig
python -c "import io; n=io.open('installer/PrivacyYouTuber.nsi',encoding='utf-8-sig').read().replace('!define VERSION \"1.0.0\"','!define VERSION \"1.4.2\"'); io.open('installer/_build_tmp.nsi','w',encoding='utf-8-sig',newline='\r\n').write(n)"
"/c/Program Files (x86)/NSIS/makensis.exe" /V2 installer/_build_tmp.nsi

# Sync frontend σε 3 σημεία
cp web/index.html web/i18n.json web/i18n.js .                                      # -> root (GitHub)
cp web/index.html web/i18n.json web/i18n.js "$LOCALAPPDATA/PrivacyYouTuber/web/"   # -> override

# Ελεγχος διαρροής secrets
python -c "d=open('dist_onedir/PrivacyYouTuber/PrivacyYouTuber.exe','rb').read(); print('CLEAN' if b'ghp_' not in d and b'sk-proj' not in d else 'LEAK')"

# Ελεγχος UI (ελαφρύς)
python scripts/check_ui.py
```

## ΚΑΤΑΣΤΑΣΗ ΠΑΡΑΔΟΤΕΩΝ (τέλος 16/10)

| Τι | Πού | Κατάσταση |
|---|---|---|
| App 1.4.2 | dist_onedir/PrivacyYouTuber/ | OK 66 MB |
| Installer 1.4.2 | dist_onedir/PrivacyYouTuber-Setup-1.4.2.exe | OK **Gumroad** |
| Desktop | C:\Users\andys\Desktop\PrivacyYouTuber\ | OK |
| Override web | %LOCALAPPDATA%\PrivacyYouTuber\web\ | OK 295 keys |
| GitHub EULA | legal/EULA-EN.md, legal/EULA-EL.md | OK link δουλεύει |
| GitHub frontend | index.html, i18n.json, i18n.js | OK |
| Gumroad περιγραφή | via API | OK discretion notice |
| Gumroad | published: True | OK |

## ΣΤΑΘΕΡΑ

- **Gumroad**: sOap88TaNJAKelU4sjM4IQ== · 14,99 EUR · https://andyspartinart.gumroad.com/l/yysgn
- **GitHub**: andyspartintrade/PrivacyYouTuber (branch main)
- **EULA links**: raw.githubusercontent.com/andyspartintrade/PrivacyYouTuber/main/legal/EULA-EN.md / EULA-EL.md
- **DB (κανονική)**: %LOCALAPPDATA%\PrivacyYouTuber\privacy_yt.db
