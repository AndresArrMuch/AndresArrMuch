// Compara el Excel de 02d1d29 con el de la rama: valores, formato de los importes y como se ven
const X = require('/tmp/claude-0/-home-user-AndresArrMuch/c0c74946-161e-5ea6-a2ae-af793f114b50/scratchpad/imp/npmxlsx/package');
const COLS = ['O','P','Q','R','S','T','U','V','W','X','Y','Z','AA'];
const load = (f) => {
  const ws = X.readFile(f, { cellNF: true, cellFormula: true }).Sheets['PLE Ventas'];
  const last = X.utils.decode_range(ws['!ref']).e.r + 1, rows = [];
  for (let r = 8; r <= last; r++) {
    if (!ws['I' + r]) continue;
    const doc = ws['I' + r].v + '-' + String(ws['J' + r].v).padStart(6, '0');
    rows.push({ doc, AJ: ws['AJ' + r]?.v, cells: COLS.map(c => { const x = ws[c + r] || {}; return { c, v: x.v, z: x.z || null, se_ve: x.z ? X.SSF.format(x.z, x.v) : String(x.v) }; }) });
  }
  const tot = (c) => rows.reduce((a, r) => a + Number(r.cells[COLS.indexOf(c)].v || 0), 0).toFixed(2);
  return { rows, totals: { P: tot('P'), R: tot('R'), AA: tot('AA') }, sub: ['P5','R5','AA5'].map(a => [a, ws[a]?.f, ws[a]?.z || null]) };
};
const a = load('v02d1d29.xlsx'), b = load('guion.xlsx');
const out = [];
out.push('Totales 02d1d29: ' + JSON.stringify(a.totals) + '\nTotales rama:    ' + JSON.stringify(b.totals) + '\nIguales: ' + (JSON.stringify(a.totals) === JSON.stringify(b.totals)));
out.push('Valores O..AA iguales fila por fila: ' + (JSON.stringify(a.rows.map(r => r.cells.map(c => c.v))) === JSON.stringify(b.rows.map(r => r.cells.map(c => c.v)))));
out.push('SUBTOTAL encabezado rama: ' + JSON.stringify(b.sub));
out.push('Celdas O..AA sin formato en la rama: ' + b.rows.flatMap(r => r.cells.filter(c => c.z !== '#,##0.00;-#,##0.00;"-"').map(c => r.doc + ' ' + c.c)).length);
out.push('\nComo se ve cada fila (rama) — O P R AA (Q y S..Z estan ocultas y tambien llevan el formato):');
for (const r of b.rows) {
  const pick = (c) => r.cells[COLS.indexOf(c)].se_ve.padStart(10);
  const ocultas = ['Q','S','T','U','V','W','X','Y','Z'].map(c => r.cells[COLS.indexOf(c)].se_ve.trim());
  out.push(`  ${r.doc.padEnd(12)} O${pick('O')} P${pick('P')} R${pick('R')} AA${pick('AA')}  AJ=${r.AJ}  ocultas: ${[...new Set(ocultas)].join(',')}`);
}
const anul = b.rows.filter(r => r.AJ === 2);
out.push('\nAnulados (AJ=2): ' + anul.map(r => r.doc + ' -> todas las O..AA se ven "-": ' + r.cells.every(c => c.se_ve.trim() === '-' && c.v === 0)).join('; '));
console.log(out.join('\n'));
