// Ελέγχει το CSS με το css parser της Node (χωρίς browser).
// Βρίσκει ΠΟΙΟΣ κανόνας κερδίζει για .pop-page-grid.
const fs = require('fs');
const h = fs.readFileSync('web/index.html', 'utf8');
const css = h.match(/<style>([\s\S]*?)<\/style>/)[1];

// Βρες ΟΛΟΥΣ τους κανόνες που επηρεάζουν το grid/label
const rules = [];
const re = /([^{}]+)\{([^{}]*)\}/g;
let m;
while ((m = re.exec(css)) !== null) {
  const sel = m[1].trim().replace(/\s+/g, ' ');
  const body = m[2].trim();
  if (sel.includes('pop-page-grid') || sel.includes('tag-pop.paged') ||
      sel.includes('tag-pop-list.paged') || sel.includes('pop-pager')) {
    rules.push({ sel, body });
  }
}

console.log('=== ΚΑΝΟΝΕΣ ΠΟΥ ΑΦΟΡΟΥΝ ΤΟ PAGINATION ===\n');
rules.forEach((r, i) => {
  console.log(`[${i + 1}] ${r.sel}`);
  console.log(`    ${r.body.replace(/\s+/g, ' ')}`);
  console.log();
});

// ── ΤΟ ΚΡΙΣΙΜΟ: είναι το .tag-pop-list.paged μετά το .tag-pop-list; ──
const idxList = css.indexOf('.tag-pop-list {');
const idxPaged = css.indexOf('.tag-pop-list.paged');
console.log('=== ΣΕΙΡΑ ===');
console.log('.tag-pop-list {        στη θέση:', idxList);
console.log('.tag-pop-list.paged {  στη θέση:', idxPaged);
console.log('✅ Το paged είναι ΜΕΤΑ:', idxPaged > idxList);

// ── Πόσοι κανόνες ορίζουν grid-template-columns για το .pop-page-grid ──
const gtc = rules.filter(r => r.sel.includes('pop-page-grid') && r.body.includes('grid-template-columns'));
console.log('\nκανόνες με grid-template-columns για pop-page-grid:', gtc.length);
gtc.forEach(r => console.log('   ', r.sel, '→', r.body.match(/grid-template-columns:[^;]*/)[0]));

// ── Το width του popup ──
const w = rules.find(r => r.sel.includes('tag-pop.paged'));
console.log('\n.tag-pop.paged width:', w ? w.body.match(/width:[^;]*/) : 'ΔΕΝ ΥΠΑΡΧΕΙ');
