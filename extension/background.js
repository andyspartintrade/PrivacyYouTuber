// Background service worker — ο «μεταφορέας» που στέλνει τα δεδομένα στον τοπικό server.
// Στο MV3, το content script ΔΕΝ μπορεί να κάνει απευθείας fetch στο localhost
// (mixed content / CORS). Αυτό εδώ έχει host_permissions και το κάνει σωστά.

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "watch") {
    fetch("http://127.0.0.1:8765/watch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(msg.details),
    })
      .then((r) => sendResponse({ ok: r.ok, status: r.status }))
      .catch((err) => sendResponse({ ok: false, error: err && err.message }));
    return true; // κράτα το κανάλι ανοιχτό για το async sendResponse
  }
});
