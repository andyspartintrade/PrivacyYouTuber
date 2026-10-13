// Τεστ: εξάγω το <script> από το index.html και ελέγχω αν η renderCatPopList
// είναι η ΝΕΑ έκδοση (με pop-page-grid) — node --check δεν το πιάνει.
const fs = require('fs');
const h = fs.readFileSync('web/index.html', 'utf8');
const scripts = [...h.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);

const all = scripts.join('\n');
console.log('ΣΥΝΟΛΟ script blocks:', scripts.length);
console.log('ΣΥΝΟΛΟ chars:', all.length);

// Έλεγξε ότι η renderCatPopList περιέχει pop-page-grid
const i = all.indexOf('function renderCatPopList');
console.log('\nrenderCatPopList βρέθηκε στη θέση:', i);
if (i >= 0) {
  const body = all.slice(i, i + 900);
  console.log('Περιέχει "pop-page-grid":', body.includes('pop-page-grid'));
  console.log('Περιέχει "_catPopPage":', body.includes('_catPopPage'));
  console.log('--- πρώτες 600 χαρ. ---');
  console.log(body.slice(0, 600));
}

// Υπάρχει ΔΙΠΛΗ δήλωση της renderCatPopList (παλιά + νέα);
const count = (all.match(/function renderCatPopList/g) || []).length;
console.log('\nΠόσες renderCatPopList υπάρχουν:', count);

// Το ίδιο για renderTagPopList
const c2 = (all.match(/function renderTagPopList/g) || []).length;
console.log('Πόσες renderTagPopList υπάρχουν:', c2);

// ΤΟ ΚΡΙΣΙΜΟ: υπάρχει ΠΑΛΙΑ έκδοση κάπου; (χωρίς pagination)
const oldCat = all.match(/function renderCatPopList[^]*?\n\}/g) || [];
console.log('\n=== ΑΝΑΛΥΣΗ ΚΑΘΕ renderCatPopList ===');
oldCat.forEach((f, n) => {
  console.log(`#${n + 1}: pop-page-grid=${f.includes('pop-page-grid')}, μήκος=${f.length}`);
});
