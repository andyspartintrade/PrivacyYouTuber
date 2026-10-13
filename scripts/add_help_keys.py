"""Προσθέτει τα keys του Takeout modal + τα λοιπά στο web/i18n.json."""
import json

NEW = {
    "help.title": ("❓ How to export from Google Takeout", "❓ Πώς κάνεις εξαγωγή από το Google Takeout"),
    "help.intro1": ("To get your YouTube", "Για να πάρεις τη λίστα"),
    "help.introB": ("subscription list", "συνδρομών"),
    "help.intro2": (", follow these steps:", "σου από το YouTube, ακολούθησε τα βήματα:"),
    "help.s1a": ("Open", "Άνοιξε το"),
    "help.s1b": ("and sign in with your account.", "και συνδέσου με τον λογαριασμό σου."),
    "help.s2a": ("Click", "Πάτησε"),
    "help.s2b": ("(above the list) to uncheck everything.", "(πάνω από τη λίστα) για να ξε-τσεκάρεις τα πάντα."),
    "help.s3a": ("Scroll down the list and check", "Κατέβα στη λίστα και τσέκαρε"),
    "help.s3only": ("only", "μόνο"),
    "help.s4a": ("Click the", "Πάτησε το κουμπί"),
    "help.s4b": ("button below it, and make sure", "κάτω από αυτό, και βεβαιώσου ότι η"),
    "help.s4c": ("is set to", "είναι σε μορφή"),
    "help.or": ("or", "ή"),
    "help.s5a": ("Click", "Πάτησε"),
    "help.s5b": ("(bottom right) → choose frequency", "(κάτω δεξιά) → διάλεξε συχνότητα"),
    "help.s6a": ("Wait for the \"Your export is ready\" email — usually", "Περίμενε το email «Η εξαγωγή σου είναι έτοιμη» — συνήθως"),
    "help.s6b": ("a few minutes", "λίγα λεπτά"),
    "help.s6c": ("(sometimes hours).", "(μερικές φορές ώρες)."),
    "help.s7a": ("Download the", "Κατέβασε το"),
    "help.s7b": (", extract it and find", ", άνοιξέ το και βρες το"),
    "help.s7c": ("→ file", "→ αρχείο"),
    "help.s8a": ("Come back here, click", "Γύρνα εδώ, πάτησε"),
    "help.s8b": (", pick the file — and", ", διάλεξε το αρχείο — και"),
    "help.s8done": ("done!", "έτοιμο!"),
    # λοιπά που έμειναν
    "misc.tags": ("🏷️ Tags", "🏷️ Tags"),
    "misc.add": ("Add", "Προσθήκη"),
    "misc.activeZero": ("· 0 active", "· 0 ενεργά"),
    "tag.addBtn": ("Add", "Προσθήκη"),
}

p = "web/i18n.json"
d = json.load(open(p, encoding="utf-8"))
added = 0
for k, (en, el) in NEW.items():
    if k not in d:
        d[k] = {"en": en, "el": el}
        added += 1
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"i18n.json: +{added} (σύνολο {len(d)})")
