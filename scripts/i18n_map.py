"""
ΤΟ ΛΕΞΙΚΟ + ο εφαρμοστής i18n.
- ΛΕΞΙΚΟ: κάθε ελληνικό string -> { key, en, el, αντικατάσταση }
- Εφαρμόζει στο web/index.html: βάζει data-i18n / data-i18n-placeholder / data-i18n-title
- Προσθέτει τα keys στο web/i18n.json
- Για JS strings που είναι ΠΕΡΙΕΧΟΜΕΝΟ (popup msgs) -> αντικαθιστά με t('key')
"""

import json
import re

INDEX = "web/index.html"
I18N = "web/i18n.json"

# ── ΛΕΞΙΚΟ: (greek_text) -> (key, en, el) ───────────────────────────────
# Χρησιμοποιείται ΚΑΙ για data-i18n ΚΑΙ για t() αντικατάσταση.

LEX = {
    # --- subs modal note ---
    "💡 Το αρχείο περιέχει": ("help.fileContains", "💡 The file contains", "💡 Το αρχείο περιέχει"),
    "🔗 Άνοιξε το Google Takeout": ("help.openTakeout", "🔗 Open Google Takeout", "🔗 Άνοιξε το Google Takeout"),
    "Κλείσιμο": ("btn.close", "Close", "Κλείσιμο"),

    # --- popovers ---
    "📁 Κατηγορία": ("pop.category", "📁 Category", "📁 Κατηγορία"),
    "📌 Καρφίτσωμα": ("pop.pin", "📌 Pin", "📌 Καρφίτσωμα"),
    "+ νέα κατηγορία": ("cat.new", "+ new category", "+ νέα κατηγορία"),

    # --- update popup ---
    "Νέα έκδοση διαθέσιμη!": ("upd.available", "New version available!", "Νέα έκδοση διαθέσιμη!"),
    "✨ Ενημέρωση τώρα": ("upd.updateNow", "✨ Update now", "✨ Ενημέρωση τώρα"),
    "Αργότερα": ("btn.later", "Later", "Αργότερα"),
    "Η εφαρμογή είναι παλιά (out of date)": ("upd.outOfDate", "The app is out of date", "Η εφαρμογή είναι παλιά (out of date)"),
    "Πρέπει να κατεβάσεις και να εγκαταστήσεις τη νέα έκδοση.": ("upd.mustInstall", "You need to download and install the new version.", "Πρέπει να κατεβάσεις και να εγκαταστήσεις τη νέα έκδοση."),
    "⬇ Κατέβασε τη νέα έκδοση": ("upd.download", "⬇ Download the new version", "⬇ Κατέβασε τη νέα έκδοση"),
    "Έχεις την τελευταία έκδοση": ("upd.latest", "You have the latest version", "Έχεις την τελευταία έκδοση"),
    "Οκ": ("btn.ok", "Ok", "Οκ"),
    "Έλεγχος απέτυχε": ("upd.checkFailed", "Check failed", "Έλεγχος απέτυχε"),
    "Ενημέρωση UI…": ("upd.uiUpdating", "Updating UI…", "Ενημέρωση UI…"),
    "Κατεβάζω το νέο interface (δεν χρειάζεται reinstall).": ("upd.downloadingUI", "Downloading the new interface (no reinstall needed).", "Κατεβάζω το νέο interface (δεν χρειάζεται reinstall)."),
    "Ενημέρωση ολοκληρώθηκε!": ("upd.done", "Update complete!", "Ενημέρωση ολοκληρώθηκε!"),
    "Κλείσε την εφαρμογή και ξανάνοιξέ την για να δεις το νέο interface.": ("upd.restart", "Close the app and reopen it to see the new interface.", "Κλείσε την εφαρμογή και ξανάνοιξέ την για να δεις το νέο interface."),
    "Η ενημέρωση απέτυχε": ("upd.failed", "Update failed", "Η ενημέρωση απέτυχε"),
    "Δεν απαντά ο server": ("msg.serverDown", "Server not responding", "Δεν απαντά ο server"),
    "Δεν απαντά ο server.": ("msg.serverDownDot", "Server not responding.", "Δεν απαντά ο server."),
    "άγνωστο σφάλμα": ("msg.unknownError", "unknown error", "άγνωστο σφάλμα"),

    # --- import mode ---
    "Πώς θες να γίνει η εισαγωγή;": ("imp.how", "How do you want the import?", "Πώς θες να γίνει η εισαγωγή;"),
    "Διάλεξε αν θα αντικατασταθούν τα τρέχοντα δεδομένα ή θα συγχωνευτούν (χωρίς διπλότυπα).": ("imp.howDesc", "Choose whether to replace the current data or merge it (no duplicates).", "Διάλεξε αν θα αντικατασταθούν τα τρέχοντα δεδομένα ή θα συγχωνευτούν (χωρίς διπλότυπα)."),
    "🔄 Αντικατάσταση": ("imp.replace", "🔄 Replace", "🔄 Αντικατάσταση"),
    "🔗 Συγχώνευση": ("imp.merge", "🔗 Merge", "🔗 Συγχώνευση"),
    "Ακύρωση": ("btn.cancel", "Cancel", "Άκυρο"),

    # --- feed ---
    "✅ Είσαι ενημερωμένος — δεν υπάρχουν νέα βίντεο.": ("feed.noNew", "✅ You are up to date — no new videos.", "✅ Είσαι ενημερωμένος — δεν υπάρχουν νέα βίντεο."),
    "Επόμενα →": ("btn.next", "Next →", "Επόμενα →"),
    "Άδεια — δες ένα βίντεο στο YouTube.": ("msg.empty", "Empty — watch a video on YouTube.", "Άδεια — δες ένα βίντεο στο YouTube."),
    "Άγνωστο κανάλι": ("msg.unknownChannel", "Unknown channel", "Άγνωστο κανάλι"),
    "ΝΕΟ": ("misc.newBadge", "NEW", "ΝΕΟ"),

    # --- delete confirms ---
    "Θα διαγραφεί το κανάλι:": ("del.channel", "The channel will be deleted:", "Θα διαγραφεί το κανάλι:"),
    "Πρόσφατες αναζητήσεις": ("search.recent", "Recent searches", "Πρόσφατες αναζητήσεις"),
    "📺 Κανάλια": ("misc.channels", "📺 Channels", "📺 Κανάλια"),
    "🎬 Βίντεο": ("misc.videos", "🎬 Videos", "🎬 Βίντεο"),
    "➕ Παρακολούθησε": ("ch.follow", "➕ Follow", "➕ Παρακολούθησε"),
    "— τέλος —": ("msg.end", "— end —", "— τέλος —"),
    "…φόρτωση βίντεο…": ("msg.loadingVideo", "…loading videos…", "…φόρτωση βίντεο…"),
    "Δεν μπόρεσα να φέρω το κανάλι.": ("msg.channelFailed", "Could not fetch the channel.", "Δεν μπόρεσα να φέρω το κανάλι."),
    "Κανένα πρόσφατο βίντεο.": ("msg.noRecentVideos", "No recent videos.", "Κανένα πρόσφατο βίντεο."),
    "Σφάλμα σύνδεσης.": ("msg.connectionError", "Connection error.", "Σφάλμα σύνδεσης."),
    "Θα σβηστεί η κατηγορία": ("del.categoryWill", "The category will be deleted", "Θα σβηστεί η κατηγορία"),
    "Τα βίντεό της θα γίνουν ακατηγοριοποίητα. Δεν ξαναγυρίζει.": ("del.categoryWarn", "Its videos will become uncategorized. This cannot be undone.", "Τα βίντεό της θα γίνουν ακατηγοριοποίητα. Δεν ξαναγυρίζει."),
    "Ακατηγοριοποίητα": ("msg.uncategorized", "Uncategorized", "Ακατηγοριοποίητα"),
    "Κανένα βίντεο.": ("msg.noVideos", "No videos.", "Κανένα βίντεο."),
    "📁 Φτιάξε κατηγορίες για να φιλτράρεις.": ("cat.makeCategories", "📁 Create categories to filter.", "📁 Φτιάξε κατηγορίες για να φιλτράρεις."),
    "(καμία κατηγορία)": ("msg.noCategory", "(no category)", "(καμία κατηγορία)"),
    "⏱️ Κανένα σημείο σημειωμένο ακόμα.": ("note.none", "⏱️ No notes yet.", "⏱️ Κανένα σημείο σημειωμένο ακόμα."),
    "Άκυρο": ("btn.cancel2", "Cancel", "Άκυρο"),
    "Αποθήκευση": ("btn.save", "Save", "Αποθήκευση"),
    "…φόρτωση…": ("msg.loading", "…loading…", "…φόρτωση…"),
    "σφάλμα δικτύου": ("msg.networkError", "network error", "σφάλμα δικτύου"),

    # --- tag panel ---
    "🏷️ Πάτα το 🏷️ σε ένα βίντεο ή κανάλι για να φτιάξεις tags.": ("tag.hint", "🏷️ Tap 🏷️ on a video or channel to create tags.", "🏷️ Πάτα το 🏷️ σε ένα βίντεο ή κανάλι για να φτιάξεις tags."),
    "Γράψε το πρώτο σου tag 👇": ("tag.writeFirst", "Write your first tag 👇", "Γράψε το πρώτο σου tag 👇"),
    "Θα σβηστεί το tag": ("tag.willBeDeleted", "The tag will be deleted", "Θα σβηστεί το tag"),
    "από": ("tag.from", "from", "από"),
    "ΟΛΑ": ("tag.all", "ALL", "ΟΛΑ"),
    "τα βίντεο και κανάλια.": ("tag.fromAll", "videos and channels.", "τα βίντεο και κανάλια."),
    "Δεν ξαναγυρίζει.": ("misc.noReturn", "It will not come back.", "Δεν ξαναγυρίζει."),
    "✓ Ναι, σβήστο": ("btn.yesDelete", "✓ Yes, delete it", "✓ Ναι, σβήστο"),
    "✕ Άκυρο": ("btn.noCancel", "✕ Cancel", "✕ Άκυρο"),

    # --- export/import status ---
    "….φτιάχνω το export…": ("io.exporting", "…building export…", "….φτιάχνω το export…"),
    "⚠️ Σφάλμα: ": ("msg.errorColon", "⚠️ Error: ", "⚠️ Σφάλμα: "),
    "✅ Αποθηκεύτηκε: ": ("io.saved", "✅ Saved: ", "✅ Αποθηκεύτηκε: "),
    "…έλεγχος…": ("upd.checking", "…checking…", "…έλεγχος…"),
    "🔄 Ενημέρωση": ("upd.button", "🔄 Update", "🔄 Ενημέρωση"),
    "Δεν κατάφερα να ελέγξω.": ("upd.couldntCheck", "Could not check.", "Δεν κατάφερα να ελέγξω."),
    "Σφάλμα": ("msg.error", "Error", "Σφάλμα"),
    "✅ Εισήχθησαν ": ("io.imported", "✅ Imported ", "✅ Εισήχθησαν "),
    " κανάλια ως «παρακολουθούμενα»": ("io.asWatched", " channels as followed", " κανάλια ως «παρακολουθούμενα»"),
    " βίντεο": ("misc.videosN", " videos", " βίντεο"),

    # --- buttons / player ---
    "Τέλος": ("btn.end", "End", "Τέλος"),
    "Λιγότερα": ("btn.less", "Show less", "Λιγότερα"),
    "Περισσότερα": ("btn.more", "Show more", "Περισσότερα"),
    "Παίξε το μέσα στην εφαρμογή": ("card.playInApp", "Play inside the app", "Παίξε το μέσα στην εφαρμογή"),
    "Πρόσθεσε στο ιστορικό μου": ("card.addToHistory", "Add to my history", "Πρόσθεσε στο ιστορικό μου"),
    "Δεν με ενδιαφέρει (δεν θα ξαναεμφανιστεί)": ("card.dismiss", "Not interested (will not show again)", "Δεν με ενδιαφέρει (δεν θα ξαναεμφανιστεί)"),
    "Άνοιξε το κανάλι στο YouTube": ("ch.openYouTube", "Open channel on YouTube", "Άνοιξε το κανάλι στο YouTube"),
    "Tags καναλιού (σε όλα τα βίντεο)": ("ch.tagsAll", "Channel tags (on all videos)", "Tags καναλιού (σε όλα τα βίντεο)"),
    "Fetch νέα βίντεο": ("ch.fetchNew", "Fetch new videos", "Fetch νέα βίντεο"),
    "Καρφίτσωμα (στην κορυφή)": ("misc.pinTop", "Pin (to top)", "Καρφίτσωμα (στην κορυφή)"),
    "Κανάλι μία θέση πάνω": ("ch.moveUp", "Channel one position up", "Κανάλι μία θέση πάνω"),
    "Κανάλι μία θέση κάτω": ("ch.moveDown", "Channel one position down", "Κανάλι μία θέση κάτω"),
    "Διαγραφή καναλιού": ("ch.delete", "Delete channel", "Διαγραφή καναλιού"),
    "Βαθμολόγησε 1-5": ("card.rate", "Rate 1-5", "Βαθμολόγησε 1-5"),
    "Παίξε το βίντεο": ("card.play", "Play video", "Παίξε το βίντεο"),
    "Κατηγορία": ("misc.category", "Category", "Κατηγορία"),
    "Lift — απογείωσέ την": ("card.lift", "Lift — raise it", "Lift — απογείωσέ την"),
    "Διαγραφή": ("btn.delete", "Delete", "Διαγραφή"),
    "Down — προσγείωσέ την": ("card.down", "Down — lower it", "Down — προσγείωσέ την"),
    "⚠️ Σφάλμα σύνδεσης — τρέχει ο server;": ("msg.connServer", "⚠️ Connection error — is the server running?", "⚠️ Σφάλμα σύνδεσης — τρέχει ο server;"),
    "Σφάλμα σύνδεσης — τρέχει ο server;": ("msg.connServerPlain", "Connection error — is the server running?", "Σφάλμα σύνδεσης — τρέχει ο server;"),
    "Δες το βίντεο": ("card.seeVideo", "See the video", "Δες το βίντεο"),
    "Δες το κανάλι": ("card.seeChannel", "See the channel", "Δες το κανάλι"),
    "✓ Παρακολουθείς": ("ch.following", "✓ Following", "✓ Παρακολουθείς"),
    "➕ Παρακολούθησε": ("ch.follow", "➕ Follow", "➕ Παρακολούθησε"),
    "Δες στο YouTube": ("card.seeYouTube", "See on YouTube", "Δες στο YouTube"),
    "Καρφίτσωμα κατηγορίας": ("cat.pin", "Pin category", "Καρφίτσωμα κατηγορίας"),
    "Κατηγορία μία θέση πάνω": ("cat.moveUp", "Category one position up", "Κατηγορία μία θέση πάνω"),
    "Κατηγορία μία θέση κάτω": ("cat.moveDown", "Category one position down", "Κατηγορία μία θέση κάτω"),
    "Διαγραφή κατηγορίας": ("cat.delete", "Delete category", "Διαγραφή κατηγορίας"),
    "Πήγαινε στο σημείο": ("note.jump", "Jump to point", "Πήγαινε στο σημείο"),
    "Τίτλος (π.χ. Πώς ρυθμίζω ISO)": ("note.titlePh", "Title (e.g. How to set ISO)", "Τίτλος (π.χ. Πώς ρυθμίζω ISO)"),
    "Σημείωση…": ("note.notePh", "Note…", "Σημείωση…"),
    "Παύση (Space)": ("player.pause", "Pause (Space)", "Παύση (Space)"),
    "Αναπαραγωγή (Space)": ("player.play", "Play (Space)", "Αναπαραγωγή (Space)"),
    "Προηγούμενο βίντεο": ("player.prev", "Previous video", "Προηγούμενο βίντεο"),
    "Κλείσε (Esc)": ("misc.closeEsc", "Close (Esc)", "Κλείσε (Esc)"),
    "Ταχύτητα αναπαραγωγής (S)": ("player.speedS", "Playback speed (S)", "Ταχύτητα αναπαραγωγής (S)"),
    "Ταχύτητα αναπαραγωγής": ("player.speed", "Playback speed", "Ταχύτητα αναπαραγωγής"),
    "Προηγούμενο βίντεο (←)": ("player.prevArrow", "Previous video (←)", "Προηγούμενο βίντεο (←)"),
    "Πίσω 20 δευτ.": ("player.back20", "Back 20s", "Πίσω 20 δευτ."),
    "Πίσω 5 δευτ.": ("player.back5", "Back 5s", "Πίσω 5 δευτ."),
    "Μπροστά 5 δευτ.": ("player.fwd5", "Forward 5s", "Μπροστά 5 δευτ."),
    "Μπροστά 20 δευτ.": ("player.fwd20", "Forward 20s", "Μπροστά 20 δευτ."),
    "Επόμενο βίντεο (→)": ("player.nextArrow", "Next video (→)", "Επόμενο βίντεο (→)"),
    "Δεν με ενδιαφέρει": ("card.notInterested", "Not interested", "Δεν με ενδιαφέρει"),
    "Σημειώσεις (N)": ("note.notesN", "Notes (N)", "Σημειώσεις (N)"),
    "Επόμενο βίντεο": ("player.next", "Next video", "Επόμενο βίντεο"),
    "Κλείσε": ("btn.close2", "Close", "Κλείσε"),
    "Σημείωσε αυτό το σημείο": ("note.markPoint", "Mark this point", "Σημείωσε αυτό το σημείο"),
    "Αλλαγή θέματος (σκοτεινό / φωτεινό)": ("misc.themeToggle", "Toggle theme (dark / light)", "Αλλαγή θέματος (σκοτεινό / φωτεινό)"),
    "…γίνεται έλεγχος…": ("lic.checking", "…checking…", "…γίνεται έλεγχος…"),
    "Δώσε το key.": ("lic.giveKey", "Enter the key.", "Δώσε το key."),

    # --- titles ---
    "Άνοιξε/κλείσε ΟΛΑ τα κανάλια": ("ch.openAll", "Expand/collapse ALL channels", "Άνοιξε/κλείσε ΟΛΑ τα κανάλια"),
    "Άνοιξε/κλείσε ΟΛΕΣ τις κατηγορίες": ("cat.openAll", "Expand/collapse ALL categories", "Άνοιξε/κλείσε ΟΛΕΣ τις κατηγορίες"),
    "Φίλτρο βάσει αστεριών": ("misc.starFilter", "Filter by stars", "Φίλτρο βάσει αστεριών"),
    "Καθάρισε τη λέξη": ("btn.clear", "Clear text", "Καθάρισε τη λέξη"),
    "Έλεγχος για νέα έκδοση": ("upd.check", "Check for a new version", "Έλεγχος για νέα έκδοση"),

    # --- placeholders ---
    "Επικόλλησε ένα YouTube link εδώ…": ("add.urlPh", "Paste a YouTube link here…", "Επικόλλησε ένα YouTube link εδώ…"),
    "Ψάξε στο ιστορικό σου (τίτλος, κανάλι, tag, κατηγορία)…": ("search.libPh", "Search your library (title, channel, tag, category)…", "Ψάξε στο ιστορικό σου (τίτλος, κανάλι, tag, κατηγορία)…"),
    "＋ νέα κατηγορία (π.χ. Χόμπι, Εργασία)…": ("cat.newPh", "＋ new category (e.g. Hobbies, Work)…", "＋ νέα κατηγορία (π.χ. Χόμπι, Εργασία)…"),
    "Ψάξε στις κατηγορίες (τίτλος, κανάλι, tag)…": ("cat.searchPh", "Search categories (title, channel, tag)…", "Ψάξε στις κατηγορίες (τίτλος, κανάλι, tag)…"),
    "Ψάξε στο YouTube…": ("search.placeholder", "Search YouTube…", "Ψάξε στο YouTube…"),
    "+ νέο tag": ("tag.new", "+ new tag", "+ νέο tag"),
    # --- remaining HTML pieces ---
    "μόνο": ("help.fileOnly", "only", "μόνο"),
    "τα κανάλια που ακολουθείς. Τίποτα άλλο από τα δεδομένα σου δεν ανεβαίνει πουθενά — όλα μένουν": ("help.fileRest", "the channels you follow. Nothing else from your data is uploaded anywhere — everything stays", "τα κανάλια που ακολουθείς. Τίποτα άλλο από τα δεδομένα σου δεν ανεβαίνει πουθενά — όλα μένουν"),
    "τοπικά": ("misc.locally", "locally", "τοπικά"),
    "τα βίντεο.": ("del.videosDot", "the videos.", "τα βίντεο."),
    "▶ Άνοιξε στο YouTube": ("card.openYT", "▶ Open on YouTube", "▶ Άνοιξε στο YouTube"),
    "🔑 Ενεργοποίηση": ("lic.title", "🔑 Activation", "🔑 Ενεργοποίηση"),
    "Βάλε το license key από το email της αγοράς σου.": ("lic.hint", "Enter the license key from your purchase email.", "Βάλε το license key από το email της αγοράς σου."),
    "✓ Ενεργοποίηση": ("lic.activate", "✓ Activate", "✓ Ενεργοποίηση"),
    "Το license δεν είναι ενεργό": ("lic.notActive", "The license is not active", "Το license δεν είναι ενεργό"),
    "🔑 Βάλε key ξανά": ("lic.reenter", "🔑 Enter key again", "🔑 Βάλε key ξανά"),
    "📝 Σημείωση": ("note.title", "📝 Note", "📝 Σημείωση"),
    "📝 Σημειώσεις": ("note.notes", "📝 Notes", "📝 Σημειώσεις"),
    "⏱️ Σημείωση εδώ": ("note.here", "⏱️ Note here", "⏱️ Σημείωση εδώ"),
    "Πρόσφατα βίντεο": ("ch.recent", "Recent videos", "Πρόσφατα βίντεο"),
    # --- import/license msgs ---
    "⚠️ Δεν απαντά ο server": ("msg.serverDownPlain", "⚠️ Server not responding", "⚠️ Δεν απαντά ο server"),
    "….εισαγωγή (αντικατάσταση)…": ("imp.loadingReplace", "….importing (replace)…", "….εισαγωγή (αντικατάσταση)…"),
    "….εισαγωγή (συγχώνευση)…": ("imp.loadingMerge", "….importing (merge)…", "….εισαγωγή (συγχώνευση)…"),
    "✅ Εισαγωγή ολοκληρώθηκε (": ("io.importDoneOpen", "✅ Import complete (", "✅ Εισαγωγή ολοκληρώθηκε ("),
    "αντικατάσταση": ("imp.modeReplace", "replace", "αντικατάσταση"),
    "συγχώνευση": ("imp.modeMerge", "merge", "συγχώνευση"),
    "Το license δεν είναι ενεργό.": ("lic.notActiveDot", "The license is not active.", "Το license δεν είναι ενεργό."),
    "Η ενεργοποίηση απέτυχε.": ("lic.failed", "Activation failed.", "Η ενεργοποίηση απέτυχε."),
    "άγνωστο": ("msg.unknown", "unknown", "άγνωστο"),
    "….εισαγωγή καναλιών…": ("imp.loadingChannels", "….importing channels…", "….εισαγωγή καναλιών…"),
    "Paste a YouTube link here…": ("add.urlPh", "Paste a YouTube link here…", "Επικόλλησε ένα YouTube link εδώ…"),
    # --- τελικό πέρασμα ---
    "⚠️ Δεν απαντά ο server": ("msg.serverDownPlain", "⚠️ Server not responding", "⚠️ Δεν απαντά ο server"),
    "Διαγραφή κατηγορίας «${esc(name)}»": ("cat.deleteNamed", "Delete category \"${esc(name)}\"", "Διαγραφή κατηγορίας «${esc(name)}»"),
    "Διαγραφή κατηγορίας «${esc(c)}» από παντού": ("cat.deleteEverywhere", "Delete category \"${esc(c)}\" everywhere", "Διαγραφή κατηγορίας «${esc(c)}» από παντού"),
    "Διαγραφή του tag «${esc(t)}» από παντού": ("tag.deleteEverywhere", "Delete tag \"${esc(t)}\" everywhere", "Διαγραφή του tag «${esc(t)}» από παντού"),
    "· 0 βίντεο": ("ch.zeroVideos", "· 0 videos", "· 0 βίντεο"),
    "Σφάλμα σύνδεσης": ("msg.connErr", "Connection error", "Σφάλμα σύνδεσης"),
}

# Keys ΜΟΝΟ για το i18n.json (χρησιμοποιούνται ΜΕΣΑ σε template literals που
# έγιναν χειροκίνητα — δεν χρειάζεται αντικατάσταση στο HTML).
EXTRA_KEYS = {
    # Settings cards
    "set.dbTitle": ("💾 Your database", "💾 Η βάση δεδομένων σου"),
    "set.dbBody1": ("Here you", "Εδώ"),
    "set.dbImport": ("import", "κάνεις εισαγωγή"),
    "set.dbBody2": ("and", "και"),
    "set.dbExport": ("export", "εξαγωγή"),
    "set.dbBody3": ("the entire app database — your channels, categories, videos, searches and tags.", "όλης της βάσης της εφαρμογής — κανάλια, κατηγορίες, βίντεο, αναζητήσεις και tags."),
    "set.exportTitle": ("📦 Export", "📦 Εξαγωγή"),
    "set.exportDesc": ("→ saves a file with everything (for backup or another computer)", "→ σώζει ένα αρχείο με τα πάντα (για backup ή άλλο υπολογιστή)"),
    "set.importTitle": ("📥 Import", "📥 Εισαγωγή"),
    "set.importDesc": ("→ brings in a database from another machine, with", "→ φέρνει βάση από άλλο μηχάνημα, με"),
    "set.replaceWord": ("Replace", "Αντικατάσταση"),
    "set.orWord": ("or", "ή"),
    "set.mergeWord": ("Merge", "Συγχώνευση"),
    "set.btnExport": ("📦 Export", "📦 Εξαγωγή"),
    "set.btnImport": ("📥 Import", "📥 Εισαγωγή"),
    "set.updTitle": ("🔄 Updates", "🔄 Ενημερώσεις"),
    "set.updBody": ("Check whether a newer version of PrivacyYouTuber is available.", "Έλεγξε αν υπάρχει νεότερη έκδοση του PrivacyYouTuber."),
    "set.btnUpdate": ("🔄 Check for updates", "🔄 Έλεγχος για ενημέρωση"),
    "set.themeTitle": ("🌗 Theme", "🌗 Θέμα"),
    "set.themeBody": ("Light or dark — whatever suits you.", "Φωτεινό ή σκοτεινό — όπως σε βολεύει."),
    "set.themeLabel": ("Dark / Light", "Σκοτεινό / Φωτεινό"),
    "set.langTitle": ("🌐 Language", "🌐 Γλώσσα"),
    "set.langBody": ("Interface language. Takes effect immediately.", "Γλώσσα διεπαφής. Αλλάζει αμέσως."),
    "set.subsTitle": ("📥 Import subscriptions (Google Takeout)", "📥 Εισαγωγή συνδρομών (Google Takeout)"),
    "set.subsBody1": ("Load your channel list from", "Φόρτωσε τη λίστα καναλιών σου από το"),
    "set.subsImpTitle": ("📥 Import Subscriptions", "📥 Εισαγωγή Συνδρομών"),
    "set.subsImpDesc": ("→ channels are added to your", "→ τα κανάλια μπαίνουν στα"),
    "set.channelsWord": ("Channels", "Κανάλια"),
    "set.subsImpDesc2": ("at the end, in yellow", "στο τέλος, με κίτρινο"),
    "set.subsFetchDesc": ("(on the yellow channel) → fetches its videos and makes it regular", "(στο κίτρινο κανάλι) → φέρνει τα βίντεό του και το κάνει κανονικό"),
    "set.btnImportSubs": ("📥 Import Subscriptions", "📥 Εισαγωγή Συνδρομών"),
    "set.btnHelp": ("❓ Help", "❓ Βοήθεια"),
    "upd.current": ("Current: v", "Τρέχουσα: v"),
    "upd.latestShort": ("Latest: v", "Τελευταία: v"),
    "upd.youHave": ("You have v", "Έχεις v"),
    "upd.andLatest": (" · the latest is v", " · η τελευταία είναι v"),
    "feed.newVideos": ("🆕 New videos (", "🆕 Νέα βίντεο ("),
    "msg.noResultsFor": ("No results found for «", "Δεν βρέθηκαν αποτελέσματα για «"),
    "msg.noCategoryParen": ("(no category)", "(καμία κατηγορία)"),
    "misc.videosWord": (" videos", " βίντεο"),
    "misc.activeWord": (" active", " ενεργά"),
    "set.langEn": ("🇬🇧 English", "🇬🇧 English"),
    "set.langEl": ("🇬🇷 Ελληνικά", "🇬🇷 Ελληνικά"),
    "del.tagBefore": ("The tag", "Το tag"),
    "del.tagAfter": ("will be deleted from", "θα σβηστεί από"),
    "del.catBefore": ("The category", "Η κατηγορία"),
    "del.catAfter": ("will be deleted from", "θα σβηστεί από"),
    "del.withVideosBefore": ("Along with its", "Μαζί με"),
    "del.withVideosAfter": ("videos. It will not come back.", "βίντεό του. Δεν ξαναγυρίζει."),
}


def main():
    html = open(INDEX, encoding="utf-8").read()
    dic = json.load(open(I18N, encoding="utf-8"))

    # 1) πρόσθεσε όλα τα keys στο i18n.json
    added = 0
    for gr, (key, en, el) in LEX.items():
        if key not in dic:
            dic[key] = {"en": en, "el": el}
            added += 1
    for key, (en, el) in EXTRA_KEYS.items():
        if key not in dic:
            dic[key] = {"en": en, "el": el}
            added += 1

    json.dump(dic, open(I18N, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"i18n.json: +{added} keys (σύνολο {len(dic)})")


if __name__ == "__main__":
    main()
