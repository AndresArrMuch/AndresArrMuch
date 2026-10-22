const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, OUT, SHOTS] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1100 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().endsWith('.css') ? r.fulfill({ body: '', contentType: 'text/css' }) : r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
  await p.fill('#email', 'gerente.fika@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1200);
  // Extractos de octubre con las dos filas de la captura
  R.extractos = await p.evaluate(async (cid) => {
    const a = await api('/api/banks/' + cid + '/conciliacion-import/bk-fika-bcp-mn', { method: 'POST', body: JSON.stringify({ filename: 'bcp_mn_oct.xlsx', rows: [
      { date: '2026-10-12', hora: '10:46:35', amount: -70000, operation_number: '01054514', description: 'A 194 9357041 0' }] }) });
    const b = await api('/api/banks/' + cid + '/conciliacion-import/bk-fika-bcp-me', { method: 'POST', body: JSON.stringify({ filename: 'bcp_me_oct.xlsx', rows: [
      { date: '2026-10-12', hora: '11:15:55', amount: 20319.30, operation_number: '08078079', description: 'DE DOLLAR HOUSE CAMBIO' }] }) });
    return [a.message, b.message];
  }, FIKA);
  await p.evaluate(() => { state.view = 'banks'; state.bankTab = 'movimiento'; renderView(); }); await p.waitForTimeout(2500);
  await p.click('.bm-kind[data-kind="own_transfer"]'); await p.waitForTimeout(800);
  await p.selectOption('#bm-from', 'bk-fika-bcp-mn'); await p.waitForTimeout(1500);
  await p.selectOption('#bm-to', 'bk-fika-bcp-me'); await p.waitForTimeout(1500);
  await p.click('.bm-row[data-lado="out"]'); await p.waitForTimeout(800);
  await p.click('.bm-row[data-lado="in"]'); await p.waitForTimeout(1500);
  R.aviso_paso2 = await p.evaluate(() => document.querySelector('#bm-card .bm-fx')?.innerText || null);
  R.error_antiguo = await p.evaluate(() => !!document.querySelector('#bm-card .bm-err'));
  await p.fill('#bm-gloss', 'Compra de dólares Dollar House'); await p.waitForTimeout(600);
  await p.evaluate(() => { const d = document.getElementById('bm-asiento'); if (d) d.open = true; });
  R.frase = await p.evaluate(() => document.querySelector('#bm-card .bm-frase')?.innerText || null);
  R.tc = await p.evaluate(() => document.querySelector('#bm-card .bm-fxinfo')?.innerText || null);
  R.asiento = await p.evaluate(() => [...document.querySelectorAll('#bm-asiento tbody tr')].map(t => t.innerText.replace(/\s+/g, ' ').trim()));
  R.pendientes = await p.evaluate(() => [...document.querySelectorAll('#bm-card .bm-check li[data-ok="0"]')].map(x => x.innerText.replace(/\s+/g, ' ')));
  R.boton_activo = await p.evaluate(() => !document.getElementById('bm-save').disabled);
  await p.locator('#bm-card .bm-fx').scrollIntoViewIfNeeded().catch(() => {});
  await p.screenshot({ path: `${SHOTS}/1_paso2_compra_dolares.png` });
  await p.locator('#bm-asiento').scrollIntoViewIfNeeded().catch(() => {});
  await p.screenshot({ path: `${SHOTS}/2_resumen_asiento.png` });
  await p.click('#bm-save'); await p.waitForTimeout(4000);
  R.resultado = await p.evaluate(() => ({ asiento: state._bm?.result?.entry_number, conc: state._bm?.result?.conc, msg: state._bm?.msg }));
  await p.screenshot({ path: `${SHOTS}/3_registrado.png` });
  R.asiento_bd = await p.evaluate(async (cid) => {
    const l = await api('/api/manual-journal/' + cid);
    const e = (l.data || [])[0]; return e ? { numero: e.entry_number, glosa: e.gloss, lineas: (e.lines || []).map(x => [x.account_code || x.chart_account_id, x.debit_amount, x.credit_amount, x.debit_amount_me, x.credit_amount_me]) } : null;
  }, FIKA);
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); await b.close();
})();
