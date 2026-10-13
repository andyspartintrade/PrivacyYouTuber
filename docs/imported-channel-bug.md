# BUG: κίτρινα «imported» κανάλια με RAW channel_id όταν φιλτράρεις με tag

## Τι συμβαίνει (14/10/2026)

Όταν ο χρήστης **φιλτράρει με tag** (π.χ. `music`), εμφανίζονται στο κάτω μέρος της λίστας
τα **«εισαγμένα» (κίτρινα) κανάλια** — με το **raw channel_id** (`UCOhKHp3b393Vpro_G9BUeKw`)
αντί το όνομα, **και με κίτρινο** φόντο (σαν να μην έχουν κατέβει βίντεο).

## Αιτία (2 μαζί)

1. **`channel_watch.name` = None για ΟΛΑ τα 81 κανάλια.**
   Το `name` γράφεται **μόνο** στο Takeout import (`set_channel_watch(id, False, name)`).
   Τα κανάλια που προστέθηκαν **χειροκίνητα** (URL/Add) δεν έχουν `name` στο `channel_watch`
   — παίρνουν το όνομα **από τα βίντεο** (`first.channel`).

2. **Το «imported» branch του `renderVideos()` τρέχει και με ενεργό φίλτρο.**
   ```js
   const existingKeys = new Set(groups.keys());   // μόνο τα κανάλια που έχουν ΤΑΙΡΙΑΣΤΑ βίντεο
   for (const cid of Object.keys(WATCHED_META)) {
     if (existingKeys.has(cid)) continue;         // ← όσα ΔΕΝ ταιριάζουν → «imported»!
     const name = meta.name || cid;               // ← name=None → ΔΕΙΧΝΕΙ ΤΟ ID
     html += `<div class="channel-group imported" ...>`   // ← ΚΙΤΡΙΝΟ
   }
   ```
   Με φίλτρο, **δεκάδες κανάλια** δεν έχουν ταιριαστά βίντεο → **όλα γίνονται κίτρινα με ID**.

## Fix (ΓΕΝΙΚΟ — να μην ξανασυμβεί)

### Α) Frontend — το «imported» branch **μόνο χωρίς φίλτρο**
```js
if (!ACTIVE_FILTER && selectedTags.size === 0 && searchRating === 0) {
  // ... το loop με τα WATCHED_META imported
}
```
Με ενεργό φίλτρο δείχνεις **μόνο ό,τι ταιριάζει** — καμία κίτρινη «ουρά».

### Β) Fallback ονόματος από τα βίντεο (για κάθε κανάλι)
```js
const name = meta.name || channelNameFromVideos(cid) || cid;
```
Όπου `channelNameFromVideos(cid)` ψάχνει στο `allVideos` ένα `v.channel` για αυτό το `channel_id`.

### Γ) Backfill (ΜΟΝΟ τοπικά, για τα υπάρχοντα):
```sql
UPDATE channel_watch SET name = (
  SELECT v.channel FROM videos v WHERE v.channel_id = channel_watch.channel_id LIMIT 1
) WHERE name IS NULL;
```
⚠️ Αυτό είναι **θεραπεία του υπάρχοντος**, όχι γενικό fix.

## Πρόληψη (για το μέλλον)
- Το `/watch_channel` endpoint **δεν στέλνει `name`** (frontend `toggleWatch`):
  `body: { channel_id, enabled: true }`. Αν το `name` είναι χρήσιμο, **περνά το** από το frontend
  (`v.channel` του πρώτου βίντεο) ή κάνε **server-side lookup** από το `videos` table.
- Ποτέ μη δείχνεις **raw channel_id** στον χρήστη — πάντα `name → videos.channel → t('msg.unknownChannel')`.
