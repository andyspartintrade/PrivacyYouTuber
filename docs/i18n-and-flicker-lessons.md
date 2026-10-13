# i18n (EN/EL switch) + pagination + flicker — μαθήματα από τη συνεδρία 13-14/10/2026

> Πηγή: PrivacyYouTuber, μετάφραση UI 100% στα αγγλικά + switch ΕΛ/ΑΓΓ + pagination popups + κυνήγι flicker.

## 1. i18n — πώς στήθηκε (μία φορά, για πάντα)

**Το σύστημα**: `web/i18n.js` (μηχανισμός) + `web/i18n.json` (284 keys, `{"key":{"en":..,"el":..}}`).
Default = **en** (ώστε τα screenshots για Gumroad να είναι αγγλικά), `localStorage` + **DB fallback**.

**Στοιχεία δέσιμου:**
- `data-i18n="key"` → `textContent`
- `data-i18n-placeholder="key"` → placeholder
- `data-i18n-title="key"` → title (tooltip)
- `t('key')` → μέσα σε JS (template literals)

**Εργαλεία (μένουν στο repo, ξαναχρησιμοποιούνται):**
- `scripts/i18n_map.py` → **ΤΟ ΛΕΞΙΚΟ** (`LEX` + `EXTRA_KEYS`). Προσθέτεις γραμμή → τρέχεις → έτοιμο.
- `scripts/i18n_apply2.py` → HTML/placeholders/titles → `data-i18n*`
- `scripts/i18n_apply_js2.py` → JS strings → `t('key')`
- `scripts/check_ui.py` → **ποια keys χρησιμοποιούνται & λείπουν**
- `scripts/smart_sweep.py` → βρίσκει αμετάφραστα (αγνοεί σχόλια/κώδικα)
- `scripts/audit_tooltips.py` → tooltips με/χωρίς μετάφραση

**ΚΑΝΟΝΑΣ: κάθε νέο string γράφεται ΕΞ ΑΡΧΗΣ δίγλωσσο.** (Απαίτηση χρήστη.)

## 2. ⛔ ΤΑ 4 ΣΦΑΛΜΑΤΑ που κόστισαν ώρες (μην τα ξανακάνεις)

### α) Ποτέ `"` μέσα σε i18n value που πάει σε **attribute**
`title="Delete category &quot;${esc(c)}&quot; everywhere"` → το `applyI18n` το βάζει **raw** → **σπάει το HTML attribute** → το element καταρρέει (η λίστα κατηγοριών άδειαζε, το chip έσπαγε).
**Λύση:** τα `data-i18n-title` δίνουν **απλό κείμενο** (`title="Delete category"`).

### β) Ποτέ `applyI18n()` μέσα σε `.map()`/`.filter()` callback
Ένα script έβαλε `applyI18n(pop || panel || overlay)` **μέσα** σε `.map(t => {...})` → το `pop` ήταν **undefined** → `ReferenceError` → **σκότωνε τη render** (κενή λίστα).
**Λύση:** hooks **ΜΕΤΑ** το `innerHTML = ...`, ποτέ μέσα σε callbacks. Έλεγξε με `grep`.

### γ) `getBoundingClientRect()` ≠ layout μέγεθος
Όταν ένα element έχει **`transform`** (`animation: pop-in` με `scale()`), το `rect` δίνει το **ΟΠΤΙΚΟ** κουτί (αλλοιωμένο, π.χ. 47px λάθος). Όταν είναι **`display:none`** → **`(0,0)`**.
**Λύση:** για υπολογισμούς θέσης χρησιμοποίησε **`offsetWidth`/`offsetHeight`** (layout box, αγνοεί transform) + `requestAnimationFrame` **μετά** το layout.

### δ) 🚨 Αποθηκευμένο DOM reference + `innerHTML` re-render = αποκολλημένο στοιχείο
Αν κρατάς `catPopBtn` και μετά το `renderCurrent()` ξαναφτιάξει τη λίστα, το reference **δείχνει σε αποκολλημένο στοιχείο** → `getBoundingClientRect()` = **(0,0)** → **το popup πηδάει πάνω αριστερά**.
**Λύση:** `if (!el.isConnected) { el = document.querySelector('[data-id="..."]'); }` **+** guard `if (r.width===0 && r.height===0) return;` **+** `data-id` στα κουμπιά.

## 3. 🚨 Το `load()` είναι πυρηνικό όπλο — μόνο για αλλαγή ΔΕΔΟΜΕΝΩΝ

Το `load()` = `fetch('/api/dashboard')` + **ξαναχτίζει 3556 κάρτες**. Κάθε περιττή κλήση = **ορατό flash (flicker) + κόστος CPU/ζέστη**.

**ΠΟΤΕ `load()`:**
- ❌ άνοιγμα/κλείσιμο popup (`closeTagPop` το έκανε → flicker στο κλείσιμο των tags)
- ❌ pin καναλιού (`togglePinChannel` το έκανε — μόνο σειρά αλλάζει)
- ❌ αλλαγή ιδιότητας κάρτας (tag/category) → **στοχευμένο update** ή τοπικό `renderCurrent()`
- ✅ **ΜΟΝΟ** όταν αλλάζουν δεδομένα: `addVideo`, `doImport`, `activateLicense`, `setLang`

**Κανόνας:** `renderCurrent()` **μέσα σε `.then()`** = η σελίδα πρόλαβε να ζωγραφίσει → **flash**. **Στοχευμένο update** της κάρτας το αποφεύγει.

## 4. Pagination στα popups (tags / categories)

- **6 ανά καρτέλα, ΚΑΘΕΤΑ** (όχι grid — απαίτηση χρήστη).
- `POP_PAGE_SIZE = 6` · `_pagerHtml(page,total,fn)` → `◀ 1 / N ▶` · `setTagPopPage`/`setCatPopPage`.
- **Σταθερό ύψος** (`.pop-page-grid { min-height: 112px }`) → η τελευταία καρτέλα δεν «πηδάει».
- `pages <= 1` → **δεν δείχνει βελάκια** (σωστό — αλλά ο χρήστης νόμισε «χαλασμένο» μέχρι να βάλει >6 items).
- Ο pager **δεν πρέπει να κλείνει το popup** → στο click-outside: `&& !e.target.closest(".pop-pager")` (το re-render αποκολλά το `e.target`).

## 5. UX αποφάσεις (κατοχυρωμένες)

- **Νέα** κατηγορία/tag → **το popup ΜΕΝΕΙ ανοιχτό** (`keepOpen=true`). **Υπάρχουσα** → κλείνει.
- **Mutual exclusion:** `openCatPop` κλείνει τα tags, `openTagPop` κλείνει τις κατηγορίες.
- **Κανάλια + κατηγορίες: ΟΛΑ ΚΛΕΙΣΤΑ σε κάθε εκκίνηση** (ταχύτητα — 3500+ κάρτες αλλιώς). Λογική: **θετική** (`expandedChannels`/`expandedCats`), όχι `collapsed*` (άδειο σύνολο = όλα ανοιχτά!).
- **Γλώσσα: θυμάται** μέσω DB (`ui_state.lang`), **όχι** localStorage (χάνεται στο WebView2).
- **Badge**: `100% local` + `N videos` + `N channels` — όλα μέσω `t()`.

## 6. Γρήγορος έλεγχος (ΕΛΑΦΡΥΣ — όχι headless browsers)

```bash
# JS syntax (1 δευτ.)
node -e "const fs=require('fs');const h=fs.readFileSync('web/index.html','utf8');const s=[...h.matchAll(/<script>([\s\S]*?)<\/script>/g)];fs.writeFileSync('_t.js',s.map(m=>m[1]).join('\n;\n'));" && node --check _t.js && rm _t.js
node --check web/i18n.js
python -c "import ast;ast.parse(open('server/app.py',encoding='utf-8').read())"
python scripts/check_ui.py     # λείπουν keys;
```

**⛔ ΜΗΝ τρέχεις `msedge --headless` για έλεγχο** — ο χρήστης ζεσταίνει τον υπολογιστή. Ο χρήστης δοκιμάζει στην εφαρμογή (η αλήθεια).

## 7. Deploy: ΠΟΥ πάνε τα frontend αρχεία

Το app σερβίρει **override πρώτα**:
```
%LOCALAPPDATA%\PrivacyYouTuber\web\   ← ΑΥΤΟ κερδίζει (index.html, i18n.json, i18n.js)
_internal\web\                        ← built-in (fallback)
```
**Για frontend αλλαγή χωρίς reinstall:** αντίγραψε `web/*` **στο override** (και στο Desktop build).
**⚠️ Ο server ψάχνει static (i18n.json) ΜΟΝΟ στο built-in** — αν λείπει από το override, το UI δείχνει raw keys (`help.title`).

## 8. Build / licensing (σύντομα)

- **NSIS** installer (`installer/PrivacyYouTuber.nsi`, `build_installer.bat`) — zlib, ελεύθερο εμπορικά.
- **`build_onedir.py`** → `dist_onedir/` + **auto-copy στο Desktop** + **auto-copy `.env`** (dev mode, `LICENSE_CHECK=off` → χωρίς serial). Χωρίς `.env` → ζητάει serial.
- **Server αλλαγές** (π.χ. `ui_state.lang`) **θέλουν rebuild**. Frontend όχι.
- Gumroad license: `GUMROAD_PRODUCT_ID`, `GUMROAD_ACCESS_TOKEN` **μόνο** σε `.env` (στο `.gitignore`). Never στο chat/κώδικα.
