// Libro Diario: mismos resultados en main y rama (numeros, totales por periodo, filtros, Excel, Estados Financieros)
// Uso: node jd_check.js <puerto> <main|rama> <salida> <fa_dir> <xlsx.full.min.js> [empresa] [zona]
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs'), path = require('path');
const [PORT, TAG, OUT, FA, XLSX_JS, CID = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433', TZ = 'America/Lima'] = process.argv.slice(2);
const FILTROS = [
  {}, { numero: 'm03' }, { numero: '-0007' }, { glosa: 'planilla' }, { origen: 'banc' }, { origen: 'ventas' }, { documento: 'rc-1' },
  { documento: 'f001' }, { cuenta: '1212' }, { cuenta: 'cuentas por pagar' }, { fecha: '2026-03-15' }, { cuenta: '1041', glosa: 'pago' },
];
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1000 }, timezoneId: TZ, acceptDownloads: true });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => {
    const u = r.request().url();
    if (u.includes('font-awesome/6.5.1/css/all.min.css')) return r.fulfill({ path: path.join(FA, 'css/all.min.css'), contentType: 'text/css' });
    const m = u.match(/font-awesome\/6\.5\.1\/webfonts\/([^?#]+)/); if (m) return r.fulfill({ path: path.join(FA, 'webfonts', m[1]) });
    if (u.includes('xlsx/0.18.5/xlsx.full.min.js')) return r.fulfill({ path: XLSX_JS, contentType: 'application/javascript' });
    return r.abort();
  });
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(1200);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', CID).catch(() => {});
  await p.evaluate(() => doLogin());
  await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 180000 }); await p.waitForTimeout(3000);
  const R = { tag: TAG, empresa: CID, zona: TZ };
  R.dashboard = await p.evaluate(() => { renderKPIs(); const a = [...document.querySelectorAll('#kpis > *')].find(x => /ASIENTOS CONTABLES/.test(x.innerText)); return a ? a.innerText.replace(/\s+/g, ' ').trim() : ''; });
  if (TAG === 'viejo') {
    // Todo con las funciones de la pantalla de main sobre la lista completa en memoria
    Object.assign(R, await p.evaluate((FILTROS) => {
      const J = state.cache.journal;
      const sorted = [...J].sort((a, b) => String(a.entry_date).localeCompare(String(b.entry_date)) || String(a.id).localeCompare(String(b.id)));
      // numero por asiento: mismo resultado que formatJournalNumber(j, sorted) pero agrupado (verificado abajo en una muestra)
      const groups = new Map(); sorted.forEach(e => { const k = String(e.entry_date).slice(0, 7); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(e); });
      const num = {}; sorted.forEach(e => { const d = new Date(e.entry_date); num[e.id] = 'M' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(groups.get(String(e.entry_date).slice(0, 7)).indexOf(e) + 1).padStart(4, '0'); });
      const muestra = sorted.filter((_, i) => i % 97 === 0).map(e => [e.id, formatJournalNumber(e, sorted)]);
      const muestra_ok = muestra.every(([id, n]) => num[id] === n);
      const label = (id) => { const acc = (state.cache.accounts || []).find(a => a.id === id); return acc ? escapeHtml(acc.account_code) + ' - ' + escapeHtml(acc.account_name || acc.name || '') : (id || '-'); };
      const porMes = {};
      J.forEach(e => { const k = String(e.entry_date).slice(0, 7); const m = porMes[k] || (porMes[k] = { asientos: 0, debe: 0, haber: 0 });
        m.asientos++; (e.lines || []).forEach(l => { m.debe += Number(l.debit_amount || 0); m.haber += Number(l.credit_amount || 0); }); });
      Object.values(porMes).forEach(m => { m.debe = Math.round(m.debe * 100) / 100; m.haber = Math.round(m.haber * 100) / 100; });
      const filtros = FILTROS.map(f => J.filter(j => {
        if (f.numero && !num[j.id].toLowerCase().includes(f.numero)) return false;
        if (f.fecha && String(j.entry_date) !== f.fecha) return false;
        if (f.origen && !String(getJournalOrigin(j).origin).toLowerCase().includes(f.origen)) return false;
        if (f.documento && !String(getJournalDocument(j)).toLowerCase().includes(f.documento)) return false;
        if (f.glosa && !String(j.gloss || '').toLowerCase().includes(f.glosa)) return false;
        if (f.cuenta && !(j.lines || []).some(l => label(l.chart_account_id).toLowerCase().includes(f.cuenta))) return false;
        return true;
      }).map(j => j.id).sort());
      return { numeros: num, muestra_formatJournalNumber_ok: muestra_ok, por_mes: porMes, filtros, total_asientos: J.length };
    }, FILTROS));
  } else {
    const q = async (params) => p.evaluate(async (params) => {
      const u = new URLSearchParams({ tz: String(new Date().getTimezoneOffset()), ...params });
      return (await api('/api/journal-entries/' + state.companyId + '/book?' + u.toString())).data;
    }, params);
    const all = await q({ all: '1' });
    R.numeros = Object.fromEntries(all.data.map(e => [e.id, e.display_number]));
    R.total_asientos = all.pagination.total;
    R.por_mes = {};
    const meses = [...new Set(all.data.map(e => String(e.entry_date).slice(0, 7)))].sort();
    for (const m of meses) { const d = await q({ period: m, per_page: '50' }); R.por_mes[m] = { asientos: d.pagination.total, debe: d.totals.debit, haber: d.totals.credit }; }
    R.filtros = [];
    for (const f of FILTROS) {
      const d = await q({ all: '1', ...(f.numero ? { number: f.numero } : {}), ...(f.glosa ? { gloss: f.glosa } : {}), ...(f.origen ? { origin: f.origen } : {}),
        ...(f.documento ? { document: f.documento } : {}), ...(f.cuenta ? { account: f.cuenta } : {}), ...(f.fecha ? { date: f.fecha } : {}) });
      R.filtros.push(d.data.map(e => e.id).sort());
    }
    // Paginacion y orden
    const p1 = await q({ page: '1', per_page: '50' }), p2 = await q({ page: '2', per_page: '50' }), pu = await q({ page: '9999', per_page: '50' });
    R.paginacion = { total: p1.pagination.total, paginas: p1.pagination.pages, p1: p1.data.length, p2: p2.data.length, ultima: [pu.pagination.page, pu.data.length],
      sin_repetidos: new Set([...p1.data, ...p2.data].map(e => e.id)).size === p1.data.length + p2.data.length };
    const o = async (sort) => (await q({ period: '2026-10', sort, per_page: '5' })).data.map(e => e.display_number + ' ' + e.entry_date);
    R.orden = { fecha_desc: await o('fecha_desc'), fecha_asc: await o('fecha_asc'), numero_asc: await o('numero_asc'), numero_desc: await o('numero_desc') };
    const monto = await q({ all: '1', amount: String(all.data[5].lines[0].debit_amount) });
    R.filtro_monto = { buscado: all.data[5].lines[0].debit_amount, encontrados: monto.pagination.total, incluye_el_asiento: monto.data.some(e => e.id === all.data[5].id) };
  }
  // Excel del Libro Diario: main sin filtros (todo); rama con "Todos los periodos" (mismo contenido esperado)
  const exportar = async (nombre, prep) => {
    await p.evaluate((prep) => { state.view = 'journal'; if (window._jdState) { const jd = _jdState(); jd.period = ''; } Object.assign(state, prep); }, prep);
    const [dl] = await Promise.all([p.waitForEvent('download', { timeout: 300000 }), p.evaluate(() => exportJournalExcel())]);
    const f = `${OUT}/jd_${TAG}_${nombre}.xlsx`; await dl.saveAs(f); return f;
  };
  const sinFiltros = { _journalNumeroFilter: '', _journalFechaFilter: '', _journalAccountFilter: '', _journalOrigenFilter: '', _journalDocFilter: '', _journalGlosaFilter: '' };
  R.excel = [await exportar('excel_todo', sinFiltros), await exportar('excel_cuenta1212_ventas', { ...sinFiltros, _journalAccountFilter: '1212', _journalOrigenFilter: 'ventas', _journalGlosaFilter: 'zzz' })];
  // Estados Financieros: mismo texto
  await p.evaluate(() => { state.view = 'financials'; renderView(); });
  await p.waitForFunction(() => !/Cargando asientos/.test(document.getElementById('panelBody').innerText), null, { timeout: 180000 }); await p.waitForTimeout(1500);
  R.estados_financieros = await p.evaluate(() => document.getElementById('panelBody').innerText.replace(/\s+/g, ' ').trim());
  await p.screenshot({ path: `${OUT}/jd_${TAG}_estados_financieros.png` });
  // Otras pantallas
  R.otras = {};
  for (const [k, v, e] of [['ventas', 'sales', { salesTab: 'invoices' }], ['inventario', 'inventory', { invTab: 'items' }], ['dashboard', 'dashboard', {}], ['plan_cuentas', 'accounts', {}]]) {
    await p.evaluate(([v, e]) => { state.view = v; Object.assign(state, e); renderView(); }, [v, e]); await p.waitForTimeout(1500);
    R.otras[k] = await p.evaluate(() => document.getElementById('panelBody').innerText.split('\n').filter(t => t.trim() && !/Actualizado/.test(t)).join(' | '));
  }
  R.errores_js = errs;
  fs.writeFileSync(`${OUT}/jd_check_${TAG}_${CID.slice(0, 4)}_${TZ.replace('/', '-')}.json`, JSON.stringify(R));
  console.log(TAG, 'listo', R.dashboard, '| asientos', R.total_asientos, '| errores', JSON.stringify(errs));
  await b.close();
})();
