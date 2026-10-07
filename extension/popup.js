// Popup — ελέγχει αν τρέχει ο τοπικός server και ανοίγει το dashboard.

const SERVER = "http://127.0.0.1:8765";
const status = document.getElementById("status");

fetch(SERVER + "/health")
  .then((r) => r.json())
  .then((d) => {
    status.textContent = "✅ Ενεργό — " + (d.videos ?? 0) + " βίντεο στη βάση";
    status.className = "ok";
  })
  .catch(() => {
    status.textContent = "⚠️ Η εφαρμογή δεν τρέχει. Άνοιξέ την πρώτα.";
    status.className = "warn";
  });

document.getElementById("open").addEventListener("click", () => {
  window.open(SERVER, "_blank");
});
