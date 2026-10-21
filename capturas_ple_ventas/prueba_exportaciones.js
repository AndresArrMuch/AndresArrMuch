// Exporta Excel PLE, TXT export-sunat y TXT Tributario de FIKA 2026-10 y devuelve filas y totales
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, BACKEND, OUT] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ timezoneId: 'America/Lima', acceptDownloads: true });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => {
    const u = r.request().url();
    if (u.includes('xlsx.full.min.js')) return r.fulfill({ path: '/tmp/claude-0/-home-user-AndresArrMuch/c0c74946-161e-5ea6-a2ae-af793f114b50/scratchpad/imp/xlsx.full.min.js', contentType: 'application/javascript' });
    if (u.endsWith('.css')) return r.fulfill({ body: '', contentType: 'text/css' });
    return r.abort();
  });
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
  await p.fill('#email', 'admin@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1500);
  const dlP = p.waitForEvent('download', { timeout: 60000 });
  await p.evaluate(async () => {
    const get = async (u) => { const r = await api(u); return r?.data?.data || r?.data || []; };
    state.cache.sales = (await get('/api/sales/' + state.companyId + '?page=1&per_page=20000')).filter(r => r.is_active !== false); // como el cargador de la pantalla
    state.cache.customers = await get('/api/customers/' + state.companyId + '?page=1&per_page=20000');
    for (const [id, v] of [['sr-year', '2026'], ['sr-month', '10']]) {
      let el = document.getElementById(id);
      if (!el) { el = document.createElement('input'); el.id = id; el.type = 'hidden'; document.body.appendChild(el); }
      el.value = v;
    }
    if (typeof XLSX === 'undefined') await new Promise((res, rej) => { const s = document.createElement('script'); s.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js'; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
    exportSalesPle();
    return true;
  });
  const dl = await dlP; const xp = OUT.replace('.json', '.xlsx'); await dl.saveAs(xp);
  const X = require('/tmp/claude-0/-home-user-AndresArrMuch/c0c74946-161e-5ea6-a2ae-af793f114b50/scratchpad/imp/npmxlsx/package');
  const wb = X.readFile(xp); const ws = wb.Sheets[wb.SheetNames[0]];
  const rows = X.utils.sheet_to_json(ws, { header: 1, defval: '' });
  R.excel = { archivo: dl.suggestedFilename(), ref: ws['!ref'], autofilter: (ws['!autofilter'] || {}).ref, encabezado_BF: rows[5][57] ?? null, filas: rows.slice(7) };
  R.txt_sunat = await p.evaluate(async () => {
    const r = await fetch('/api/sales/' + state.companyId + '/reports/periodic/export-sunat', { method: 'POST', headers: { Authorization: 'Bearer ' + state.token, 'Content-Type': 'application/json' }, body: JSON.stringify({ period_year: 2026, period_month: 10 }) });
    return { status: r.status, texto: await r.text() };
  });
  R.txt_tributario = await p.evaluate(async () => {
    const r = await api('/api/tax/' + state.companyId + '/ple/export', { method: 'POST', body: JSON.stringify({ register_type: 'sales_register', period_year: 2026, period_month: 10 }) });
    return r?.data;
  });
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1));
  await b.close();
})();
