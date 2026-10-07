# Πλάνο — Κατηγορίες Tags (Tag Categories / Folders) — v2 (future-proof)

## Στόχος

Να μπορεί ο χρήστης να οργανώνει τα tags του σε **κατηγορίες** (δικές του, π.χ. «Εργασία», «Χόμπι», «Οικογένεια»), ώστε όταν τα tags γίνουν πολλά (30+), το φίλτρο να μένει **καθαρό και οργανωμένο** αντί για μια ατελείωτη οριζόντια λίστα.

**Διαφορά v2:** η αρχιτεκτονική σχεδιάζεται ώστε να στηρίξει από την αρχή τα μελλοντικά: **drag & drop tag μεταξύ κατηγοριών, μετονομασία/διαγραφή κατηγορίας, μετρητής χρήσης**.

## Αποφάσεις UX (κλειδωμένες με τον Ανδρίκο)

1. **Δημιουργία κατηγοριών:** μέσα από το 🏷️ popover — όταν γράφει νέο tag, επιλέγει (ή δημιουργεί) και κατηγορία.
2. **Ένα tag → πολλές κατηγορίες** (labels, σαν Gmail — ΟΧΙ αυστηρό folder).
3. **Tag χωρίς κατηγορία** → ειδική ομάδα **«Χωρίς κατηγορία»** στο τέλος του φίλτρου.
4. **Φίλτρο** → πτυχωτό πάνελ (accordion) ανά κατηγορία, μέσα κάθε κατηγορία tags σε **grid αλφαβητικά**, + **mini-search** πάνω-πάνω.

## Data model (future-proof)

**Βασική αρχή:** οι κατηγορίες ΔΕΝ είναι strings μέσα στα tags — έχουν **δικό τους πίνακα με `id`**. Τα tags συνδέονται με κατηγορίες μέσω **association πίνακα** (many-to-many). Αυτό κάνει τη **μετονομασία** (= 1 UPDATE στο name) και τη **διαγραφή** (= 1 DELETE + αποσύνδεση) καθαρές operations, και αφήνει τον **μετρητή χρήσης** να μπει φυσικά αργότερα.

### Πίνακες (ολοκληρωμένοι, μπαίνουν ΟΛΟΙ τώρα — ενεργοποιούνται σταδιακά)

```sql
-- Οι κατηγορίες ως οντότητες (για rename/delete αργότερα)
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,     -- π.χ. "Εργασία", "Χόμπι"
    created_at  TEXT
);

-- Σύνδεση tag <-> κατηγορία (many-to-many)
CREATE TABLE IF NOT EXISTS tag_categories (
    tag_id      TEXT NOT NULL,            -- το tag name (string, ΟΧΙ FK — τα tags είναι flat)
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (tag_id, category_id)
);

-- Μετρητής χρήσης ανά tag (ενεργοποιείται ΑΡΓΟΤΕΡΑ — εδώ στήνεται η δομή)
CREATE TABLE IF NOT EXISTS tag_stats (
    tag          TEXT PRIMARY KEY,
    use_count    INTEGER DEFAULT 0,       -- πόσες φορές χρησιμοποιήθηκε (βάλθηκε σε βίντεο/κανάλι ή φιλτράρεται)
    last_used_at TEXT
);
```

**Σημείωση για το `tag_id`:** τα tags παραμένουν strings (δεν έχουν δικό τους πίνακα) γιατί ζουν flat μέσα στα `videos.my_tags` + `channel_tags.tags`. Η σύνδεση `tag_id = tag name` είναι σκόπιμη — αποφεύγουμε διπλή πηγή αλήθειας για τα tags. Αν αργότερα θέλουμε tag-level metadata (χρώμα, εικονίδιο), φτιάχνουμε τότε πίνακα `tags(id, name)` και κάνουμε migration.

### Συναρτήσεις db.py

- `set_tag_categories(tag, category_names)` — δέχεται ΟΝΟΜΑΤΑ κατηγοριών, τα κάνει insert-or-get σε `categories`, και αντικαθιστά τις συνδέσεις στο `tag_categories` (DELETE + INSERT). Το API κρατάται απλό (ο frontend δίνει names, όχι ids).
- `tag_categories_map()` — `{tag: [category_name, ...]}` (join categories), για το dashboard.
- `all_categories()` — ταξινομημένη λίστα ονομάτων.
- `rename_category(old_name, new_name)` — UPDATE name (ΜΕΛΛΟΝΤΙΚΑ).
- `delete_category(name)` — DELETE + οι συνδέσεις φεύγουν με ON DELETE CASCADE (ΜΕΛΛΟΝΤΙΚΑ).
- `increment_tag_use(tag)` — use_count +1 + last_used_at (ΜΕΛΛΟΝΤΙΚΑ, για «συχνά» ταξινόμηση).

## Αλλαγές ανά αρχείο (φάση 1 — μόνο δημιουργία + προβολή)

### 1. `server/db.py`

- Προσθήκη των 3 πινάκων στο SCHEMA (categories, tag_categories, tag_stats — όλοι τώρα, οι 2 πρώτοι ενεργοί).
- Συναρτήσεις `set_tag_categories`, `tag_categories_map`, `all_categories`.

### 2. `server/app.py`

- `GET /api/dashboard` → `"tag_categories": db.tag_categories_map()`, `"all_categories": db.all_categories()`.
- Νέο `POST /set_tag_categories` `{tag, categories:[...]}`.

### 3. `web/index.html` — globals

- `TAG_CATEGORIES = {}` (map tag→categories[]).
- `ALL_CATEGORIES = []`.

### 4. `web/index.html` — popover (🏷️)

- Στο νέο-tag field, δίπλα και **κατηγορία** (dropdown με τα ALL_CATEGORIES + δημιουργία νέας).
- Αποθηκεύει `POST /set_tag_categories`.

### 5. `web/index.html` — φίλτρο (`renderTagFilter`)

- Γίνεται **πτυχωτό πάνελ**: `🏷️ Φίλτρο ▾` → ανοίγει.
- Μέσα: `[🔍 mini search]` + accordion ανά κατηγορία (grid αλφαβητικό μέσα) + «Χωρίς κατηγορία» στο τέλος.

### 6. CSS

- `.tag-filter-panel`, `.cat-group`, `.cat-head` (chevron + name + count), `.tag-grid`, `.tag-mini-search`.

## Φάση 2 (μελλοντικά, ήδη «στρωμένο» το έδαφος)

- **Drag & drop** tag-chip μεταξύ κατηγοριών → HTML5 draggable + `POST /set_tag_categories`.
- **Μετονομασία / διαγραφή κατηγορίας** → κουμπάκια ✎ / 🗑 στο `.cat-head` → `rename_category` / `delete_category`.
- **Μετρητής χρήσης** → `increment_tag_use` σε κάθε tag εφαρμογή + ταξινόμηση «συχνά πρώτα».

## Κίνδυνοι / παγίδες

- **Μην αγγίξεις** `unionFilters`, `applyRatingFilter`, `videoTags`, `matchInfo` — η κατηγοριοποίηση είναι ΜΟΝΟ οργάνωση, ΟΧΙ φιλτράρισμα.
- **Frozen DB path** — δοκιμή στο `%LOCALAPPDATA%\PrivacyYouTuber\privacy_yt.db` (το `data/privacy_yt.db` είναι dev).
- Backtick/quote template literal → `node --check` πριν build.
- Το mini-search φιλτράρει **οπτικά** τα tags (εύρεση), ΟΧΙ τα αποτελέσματα.

## Σειρά εκτέλεσης (φάση 1)

1. db.py (3 πίνακες + set/map/all).
2. app.py (payload + endpoint).
3. globals + φόρτωση.
4. renderTagFilter (accordion + grid + mini-search).
5. popover (κατηγορία).
6. CSS.
7. check + build + Desktop.
