/* ============================================================================
   PrivacyYouTuber — i18n (διεθνοποίηση)
   ----------------------------------------------------------------------------
   Αγγλικά = default · Ελληνικά = δεύτερη γλώσσα
   Χρήση:  t('btn.next')            → «Next →» ή «Επόμενα →»
           applyI18n(root)          → μεταφράζει ό,τι έχει data-i18n="key"
           setLang('el')            → αλλάζει γλώσσα (αποθηκεύεται τοπικά)
   ============================================================================ */
(function () {
  'use strict';

  var DEFAULT_LANG = 'en';
  var SUPPORTED = ['en', 'el'];
  var DICT = {};          // { key: {en: "...", el: "..."} }
  var LANG = DEFAULT_LANG;

  /* ── Φόρτωση λεξικού ──────────────────────────────────────────────────── */
  function loadDict(cb) {
    // Προσπάθησε fetch (όταν σερβίρεται από τον server), αλλιώς inline fallback.
    fetch('i18n.json')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (j) { DICT = j; }
        cb();
      })
      .catch(function () { cb(); });
  }

  /* ── Γλώσσα ───────────────────────────────────────────────────────────── */
  function detectLang() {
    try {
      var saved = localStorage.getItem('pyt_lang');
      if (saved && SUPPORTED.indexOf(saved) >= 0) return saved;
      var nav = (navigator.language || 'en').slice(0, 2).toLowerCase();
      if (SUPPORTED.indexOf(nav) >= 0) return nav;
    } catch (e) { /* ignore */ }
    return DEFAULT_LANG;
  }

  function getLang() { return LANG; }

  function setLang(lang) {
    if (SUPPORTED.indexOf(lang) < 0) lang = DEFAULT_LANG;
    LANG = lang;
    try { localStorage.setItem('pyt_lang', lang); } catch (e) { /* ignore */ }
    applyI18n(document);
    document.documentElement.setAttribute('lang', lang);
    // Ειδοποίησε την εφαρμογή (αν θέλει να ξαναζωγραφίσει κάτι)
    try {
      window.dispatchEvent(new CustomEvent('pyt:langchange', { detail: { lang: lang } }));
    } catch (e) { /* ignore */ }
  }

  /* ── Μετάφραση ────────────────────────────────────────────────────────── */
  function t(key, fallback) {
    var e = DICT[key];
    if (!e) return (fallback !== undefined ? fallback : key);
    return e[LANG] || e[DEFAULT_LANG] || (fallback !== undefined ? fallback : key);
  }

  /* ── Εφαρμογή σε DOM ──────────────────────────────────────────────────── */
  function applyI18n(root) {
    root = root || document;
    var nodes = root.querySelectorAll('[data-i18n]');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var key = el.getAttribute('data-i18n');
      var val = t(key);
      var attr = el.getAttribute('data-i18n-attr');
      if (attr) {
        el.setAttribute(attr, val);
      } else {
        el.textContent = val;
      }
    }
    // placeholders — ΠΑΝΤΑ μέσω setAttribute (ασφαλές: δεν σπάει το HTML)
    var phs = root.querySelectorAll('[data-i18n-placeholder]');
    for (var j = 0; j < phs.length; j++) {
      phs[j].setAttribute('placeholder', t(phs[j].getAttribute('data-i18n-placeholder')));
    }
    // titles (tooltips) — ΠΑΝΤΑ μέσω setAttribute
    var tts = root.querySelectorAll('[data-i18n-title]');
    for (var k = 0; k < tts.length; k++) {
      tts[k].setAttribute('title', t(tts[k].getAttribute('data-i18n-title')));
    }
  }

  /* ── Δημόσιο API ──────────────────────────────────────────────────────── */
  window.i18n = {
    t: t,
    setLang: setLang,
    getLang: getLang,
    apply: applyI18n,
    supported: SUPPORTED.slice(),
    ready: false
  };
  window.t = t;   // σύντομη πρόσβαση

  /* ── Εκκίνηση ─────────────────────────────────────────────────────────── */
  LANG = detectLang();
  document.documentElement.setAttribute('lang', LANG);
  loadDict(function () {
    window.i18n.ready = true;
    applyI18n(document);
    try {
      window.dispatchEvent(new CustomEvent('pyt:i18nready'));
    } catch (e) { /* ignore */ }
  });
})();
