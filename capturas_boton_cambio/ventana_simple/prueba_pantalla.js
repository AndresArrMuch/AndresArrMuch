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
  if (MODO === 'manual' || MODO === 'simple_manual') await p.evaluate(() => { window.__sinME = true; });
  await p.evaluate(async (cid) => {
    await api('/api/banks/' + cid + '/conciliacion-import/bk-fika-bcp-mn', { method: 'POST', body: JSON.stringify({ filename: 'bcp_mn_oct.xlsx', rows: [
      { date: '2026-10-21', hora: '10:02:11', amount: -343800, operation_number: '03001748', description: 'VEN U$ 3.4380 500296' }] }) });
    if (!window.__sinME) await api('/api/banks/' + cid + '/conciliacion-import/bk-fika-bcp-me', { method: 'POST', body: JSON.stringify({ filename: 'bcp_me_oct.xlsx', rows: [
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
  } else if (MODO === 'simple' || MODO === 'simple_manual') {
    const campos = () => p.evaluate(() => Object.fromEntries(['cambio-fecha','cambio-desc','cambio-op-salida','cambio-op-entrada','cambio-monto-salida','cambio-monto-entrada','cambio-cuenta-salida-texto','cambio-cuenta-entrada-texto'].map(id => [id, document.getElementById(id)?.value])));
    R.panel_texto = await p.evaluate(() => document.querySelector('#cambio-modal')?.innerText.replace(/\s+/g, ' '));
    R.campos_al_abrir = await campos();
    await p.screenshot({ path: SHOTS + '/' + MODO + '_1_abierto.png' });
    if (MODO === 'simple_manual') {
      // Primero un monto equivocado (US$ 10,000): el servidor lo rechaza y el aviso sale en la ventana
      await p.fill('#cambio-op-entrada', '04001749'); await p.fill('#cambio-monto-entrada', '10000');
      await p.click('#cambio-modal-save'); await p.waitForTimeout(2500);
      R.error_en_ventana = await p.evaluate(() => document.getElementById('cambio-error')?.innerText);
      await p.screenshot({ path: SHOTS + '/' + MODO + '_2_error.png' });
      await p.fill('#cambio-monto-entrada', '100000');
    }
    R.campos_al_registrar = await campos();
    await p.click('#cambio-modal-save'); await p.waitForTimeout(5000);
    R.panel_cerrado = await p.evaluate(() => !document.getElementById('cambio-modal'));
    R.aviso = await p.evaluate(() => [...document.querySelectorAll('.notice, [id*="notice"]')].map(x => x.innerText).join(' | ').slice(0, 300));
    R.fila_conciliacion = await p.evaluate(() => [...document.querySelectorAll('#conc-tabla-tbody tr.conc-tabla-row')].map(r => r.innerText.replace(/\s+/g, ' ')).filter(t => t.includes('03001748')));
    await p.screenshot({ path: SHOTS + '/' + MODO + '_3_registrado.png' });
    R.asiento_bd = await p.evaluate(async (cid) => { const l = await api('/api/manual-journal/' + cid); const e = (l.data || [])[0]; return e ? (e.lines || []).map(x => [x.debit_amount, x.credit_amount, x.debit_amount_me, x.credit_amount_me]) : null; }, FIKA);
  } else if (MODO === 'manual') {
    R.texto_panel = await p.evaluate(() => document.querySelector('#cambio-modal')?.innerText.replace(/\s+/g, ' ').slice(0, 400));
    await p.fill('#cambio-monto2', '100000'); await p.locator('#cambio-monto2').dispatchEvent('change'); await p.waitForTimeout(500);
    await p.fill('#cambio-op2', '04001749'); await p.locator('#cambio-op2').dispatchEvent('change'); await p.waitForTimeout(800);
    R.tc = await p.evaluate(() => document.querySelector('#cambio-modal .cambio-tc')?.innerText || null);
    await p.screenshot({ path: SHOTS + '/panel_manual.png' });
    await p.click('#cambio-modal-save'); await p.waitForTimeout(5000);
    R.aviso = await p.evaluate(() => [...document.querySelectorAll('.notice, [id*="notice"]')].map(x => x.innerText).join(' | ').slice(0, 300));
    R.fila_conciliacion = await p.evaluate(() => [...document.querySelectorAll('#conc-tabla-tbody tr.conc-tabla-row')].map(r => r.innerText.replace(/\s+/g, ' ')).filter(t => t.includes('03001748')));
  } else {
    R.panel_abierto = await p.evaluate(() => !!document.getElementById('cambio-modal'));
    R.vista = await p.evaluate(() => state.view + '/' + state.bankTab);
    R.filas_ofrecidas = await p.evaluate(() => [...document.querySelectorAll('#cambio-modal .cambio-fila2')].map(x => x.innerText.replace(/\s+/g, ' ')));
    await p.screenshot({ path: SHOTS + '/panel_1_abierto.png' });
    await p.click('#cambio-modal .cambio-fila2'); await p.waitForTimeout(800);
    R.tc = await p.evaluate(() => document.querySelector('#cambio-modal .cambio-tc')?.innerText || null);
    R.asiento = await p.evaluate(() => [...document.querySelectorAll('#cambio-modal .cambio-asiento tr')].map(t => t.innerText.replace(/\s+/g, ' ').trim()));
    R.boton_activo = await p.evaluate(() => !document.getElementById('cambio-modal-save').disabled);
    await p.screenshot({ path: SHOTS + '/panel_2_listo.png' });
    await p.click('#cambio-modal-save'); await p.waitForTimeout(5000);
    R.panel_cerrado = await p.evaluate(() => !document.getElementById('cambio-modal'));
    R.aviso = await p.evaluate(() => [...document.querySelectorAll('.notice, [id*="notice"]')].map(x => x.innerText).join(' | ').slice(0, 300));
    R.fila_conciliacion = await p.evaluate(() => [...document.querySelectorAll('#conc-tabla-tbody tr.conc-tabla-row')].map(r => r.innerText.replace(/\s+/g, ' ')).filter(t => t.includes('03001748')));
    await p.screenshot({ path: SHOTS + '/panel_3_registrado.png' });
    // Otra cuenta: la entrada del BCP ME ya quedo conciliada
    await p.evaluate(async () => { state._concAccount = 'bk-fika-bcp-me'; renderView(); await cargarExcelPersistidoConciliacion(); }); await p.waitForTimeout(2500);
    R.fila_me = await p.evaluate(() => [...document.querySelectorAll('#conc-tabla-tbody tr.conc-tabla-row')].map(r => r.innerText.replace(/\s+/g, ' ')).filter(t => t.includes('04001749')));
    // Manual: otra fila sin la del otro lado en el extracto
  }
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); await b.close();
})();
