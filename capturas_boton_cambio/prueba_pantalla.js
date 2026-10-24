// Boton "Cambio" de la Conciliacion con los datos de la captura (21/10/2026, S/ 343,800 -> US$ 100,000)
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, OUT, SHOTS, MODO] = process.argv.slice(2);   // MODO: main | rama
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1100 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().endsWith('.css') ? r.fulfill({ body: '', contentType: 'text/css' }) : r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
  await p.fill('#email', 'gerente.fika@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1200);
  await p.evaluate(async (cid) => {
    await api('/api/banks/' + cid + '/conciliacion-import/bk-fika-bcp-mn', { method: 'POST', body: JSON.stringify({ filename: 'bcp_mn_oct.xlsx', rows: [
      { date: '2026-10-21', hora: '10:02:11', amount: -343800, operation_number: '03001748', description: 'VEN U$ 3.4380 500296' }] }) });
    await api('/api/banks/' + cid + '/conciliacion-import/bk-fika-bcp-me', { method: 'POST', body: JSON.stringify({ filename: 'bcp_me_oct.xlsx', rows: [
      { date: '2026-10-21', hora: '10:02:12', amount: 100000, operation_number: '04001749', description: 'COM U$ 3.4380 500296' }] }) });
  }, FIKA);
  await p.evaluate(async () => { state.view = 'banks'; state.bankTab = 'conciliacion'; state._concAccount = 'bk-fika-bcp-mn'; state._concMonth = '2026-10'; state._concYear = '2026'; renderView(); await cargarExcelPersistidoConciliacion(); });
  await p.waitForTimeout(3000);
  const btn = p.locator('.conc-cambio-moneda-btn[data-op="03001748"]');
  R.boton_cambio = await btn.count();
  await btn.first().click(); await p.waitForTimeout(2500);
  if (MODO === 'main') {
    // Ventana antigua: se llena como en la captura
    await p.fill('#cambio-desc', 'VEN U$ 3.4380 500296'); await p.fill('#cambio-op-entrada', '04001749');
    await p.fill('#cambio-monto-salida', '343800'); await p.fill('#cambio-monto-entrada', '100000');
    const opt = await p.evaluate(() => [...document.querySelectorAll('#cambio-cuentas-datalist option')].map(o => o.value));
    await p.fill('#cambio-cuenta-salida-texto', opt.find(v => v.startsWith('104101')));
    await p.fill('#cambio-cuenta-entrada-texto', opt.find(v => v.startsWith('104102')));
    await p.screenshot({ path: `${SHOTS}/main_1_ventana_antigua.png` });
    await p.click('#cambio-modal-save'); await p.waitForTimeout(2500);
    R.aviso = await p.evaluate(() => [...document.querySelectorAll('.notice, [id*="notice"]')].map(x => x.innerText).join(' | ').slice(0, 400));
    await p.screenshot({ path: `${SHOTS}/main_2_no_se_puede.png` });
  } else {
    R.pantalla = await p.evaluate(() => ({ vista: state.view + '/' + state.bankTab, tipo: state._bm?.form?.kind, salida: state._bm?.form?.rowOut?.operation_number }));
    await p.selectOption('#bm-to', 'bk-fika-bcp-me'); await p.waitForTimeout(2000);
    await p.click('.bm-row[data-lado="in"]'); await p.waitForTimeout(1500);
    await p.fill('#bm-gloss', 'Compra de dólares BCP (VEN U$ 3.4380)'); await p.waitForTimeout(600);
    await p.evaluate(() => { const d = document.getElementById('bm-asiento'); if (d) d.open = true; });
    R.aviso_paso2 = await p.evaluate(() => document.querySelector('#bm-card .bm-fx')?.innerText || null);
    R.tc = await p.evaluate(() => document.querySelector('#bm-card .bm-fxinfo')?.innerText || null);
    R.asiento = await p.evaluate(() => [...document.querySelectorAll('#bm-asiento thead tr, #bm-asiento tbody tr, #bm-asiento tfoot tr')].map(t => t.innerText.replace(/\s+/g, ' ').trim()));
    R.pendientes = await p.evaluate(() => [...document.querySelectorAll('#bm-card .bm-check li[data-ok="0"]')].map(x => x.innerText.replace(/\s+/g, ' ')));
    await p.locator('#bm-card .bm-fx').scrollIntoViewIfNeeded().catch(() => {});
    await p.screenshot({ path: `${SHOTS}/rama_1_cambio_abre_guia.png` });
    await p.locator('#bm-asiento').scrollIntoViewIfNeeded().catch(() => {});
    await p.screenshot({ path: `${SHOTS}/rama_2_asiento.png` });
    await p.click('#bm-save'); await p.waitForTimeout(4000);
    R.resultado = await p.evaluate(() => ({ asiento: state._bm?.result?.entry_number, conc: state._bm?.result?.conc, msg: state._bm?.msg }));
    await p.screenshot({ path: `${SHOTS}/rama_3_registrado.png` });
  }
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); await b.close();
})();
