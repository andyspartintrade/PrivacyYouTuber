// Privacy YouTuber — content script.
// Βάζει ένα κουμπάκι "＋ Add" ΔΕΞΙΑ πάνω στο video player (στη μέση, vertical center).
// Όταν το πατάς → στέλνει το URL + metadata στον τοπικό server (127.0.0.1).

/* --- Ανθεκτική εξαγωγή video ID (όλα τα format) --- */
function getVideoId() {
  const href = window.location.href;
  try {
    const u = new URL(href);
    const p = u.pathname;
    // /shorts/<id>  /embed/<id>  /live/<id>  /v/<id>
    const m = p.match(/\/(shorts|embed|live|v)\/([A-Za-z0-9_-]{11})/);
    if (m) return m[2];
    // ?v=<id>
    const v = u.searchParams.get("v");
    if (v) return v;
  } catch (e) {}
  // Τελευταία καταφυγή: regex απευθείας στο href
  const m2 = href.match(/[?&]v=([A-Za-z0-9_-]{11})/);
  if (m2) return m2[1];
  return null;
}

function extractDetails() {
  try {
    const p = window.ytInitialPlayerResponse;
    if (p && p.videoDetails && p.videoDetails.videoId) {
      return {
        video_id: p.videoDetails.videoId,
        title: p.videoDetails.title,
        channel: p.videoDetails.author,
        channel_id: p.videoDetails.channelId,
        description: (p.videoDetails.shortDescription || "").slice(0, 2000),
        category:
          (p.microformat &&
            p.microformat.playerMicroformatRenderer &&
            p.microformat.playerMicroformatRenderer.category) ||
          null,
        tags: p.videoDetails.keywords || [],
      };
    }
  } catch (e) {
    /* αγνόησε */
  }

  // Fallback: από τον τίτλο της σελίδας (αν λείπει το ytInitialPlayerResponse).
  try {
    const vid = getVideoId();
    if (!vid) return null;
    let title = document.title || "";
    title = title.replace(/\s*-\s*YouTube\s*$/i, "").trim();
    return {
      video_id: vid,
      title: title,
      channel: "",
      channel_id: "",
      description: "",
      category: null,
      tags: [],
    };
  } catch (e) {
    /* αγνόησε */
  }
  return null;
}

function send(details) {
  if (!details || !details.video_id) return;
  chrome.runtime.sendMessage({ type: "watch", details }, (resp) => {
    if (chrome.runtime.lastError) {
      console.error("[privacy-yt] FAILED:", chrome.runtime.lastError.message);
      flash("⚠ Σφάλμα: δεν έφτασε στον server");
      return;
    }
    if (resp && resp.ok) {
      flash("✓ Προστέθηκε: " + (details.title || details.video_id).slice(0, 40));
    } else {
      flash("⚠ " + ((resp && resp.error) || "σφάλμα"));
    }
  });
}

/* --- Βρες τον video player container για να αγκυρώσεις το κουμπί --- */
function findPlayerContainer() {
  // Το νέο YouTube χρησιμοποιεί είτε #movie_player (div) είτε ένα <video>.
  const movie = document.querySelector("#movie_player, .html5-video-player, .html5-video-container");
  if (movie) return movie;
  const video = document.querySelector("video.html5-main-video, video");
  if (video) return video;
  return null;
}

/* --- Το κουμπάκι "＋ Add" --- */
let btn = null;

function ensureButton() {
  const anchor = findPlayerContainer();
  if (!anchor) return;

  if (btn && document.body.contains(btn)) return btn;

  btn = document.createElement("button");
  btn.id = "privacy-yt-add";
  btn.textContent = "＋ Add";
  btn.title = "Πρόσθεσε στο Privacy YouTuber";
  btn.style.cssText = [
    "position:absolute", "top:50%", "right:12px",
    "transform:translateY(-50%)", "z-index:2147483647",
    "background:rgba(108,140,255,0.92)", "color:#fff", "border:none", "border-radius:8px",
    "padding:9px 16px", "font:600 13px system-ui, Segoe UI, sans-serif",
    "cursor:pointer", "box-shadow:0 4px 16px rgba(0,0,0,.55)", "transition:background .12s",
  ].join(";");
  btn.addEventListener("mouseenter", () => { btn.style.background = "rgba(90,122,240,0.96)"; });
  btn.addEventListener("mouseleave", () => { btn.style.background = "rgba(108,140,255,0.92)"; });
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    e.preventDefault();
    const d = extractDetails();
    if (d) {
      send(d);
    } else {
      flash("⚠ Δεν βρήκα το βίντεο ακόμα, δοκίμασε ξανά");
    }
  });

  // Αγκύρωσε το κουμπί πάνω στον player (ο player πρέπει να έχει position:relative).
  const anchorStyle = getComputedStyle(anchor);
  if (anchorStyle.position === "static") {
    anchor.style.position = "relative";
  }
  anchor.appendChild(btn);
  return btn;
}

/* --- Toast επιβεβαίωσης --- */
let flashEl = null;
function flash(msg) {
  if (flashEl) flashEl.remove();
  flashEl = document.createElement("div");
  flashEl.textContent = msg;
  flashEl.style.cssText = [
    "position:fixed", "top:16px", "left:50%", "transform:translateX(-50%)",
    "z-index:2147483647", "background:#0d1017", "color:#22d3a5",
    "border:1px solid #242b38", "border-radius:8px", "padding:8px 16px",
    "font:600 13px system-ui, Segoe UI, sans-serif", "box-shadow:0 4px 16px rgba(0,0,0,.5)",
  ].join(";");
  document.body.appendChild(flashEl);
  setTimeout(() => { if (flashEl) flashEl.remove(); flashEl = null; }, 2000);
}

/* --- Εμφάνιση του κουμπιού μόνο σε watch σελίδες --- */
function maybeShow() {
  const vid = getVideoId();
  if (vid) {
    // Ο player μπορεί να μην υπάρχει ακόμα· περίμενε λίγο.
    persist();
  } else if (btn) {
    btn.remove();
    btn = null;
  }
}

function persist() {
  let trials = 0;
  const t = setInterval(() => {
    if (ensureButton()) {
      clearInterval(t);
      return;
    }
    if (++trials > 40) clearInterval(t); // ~20 δευτ.
  }, 500);
}

window.addEventListener("yt-navigate-finish", () => { if (btn) { btn.remove(); btn = null; } maybeShow(); });
document.addEventListener("yt-navigate-finish", () => { if (btn) { btn.remove(); btn = null; } maybeShow(); });

// Ξεκίνα αμέσως + ξαναπροσπάθησε σε 3, 6, 12 δευτ. (για αργό player load).
maybeShow();
setTimeout(maybeShow, 3000);
setTimeout(maybeShow, 6000);
setTimeout(maybeShow, 12000);
