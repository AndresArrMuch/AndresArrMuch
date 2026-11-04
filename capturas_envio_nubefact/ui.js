// Pantalla: venta que no llega a NubeFact, venta repetida, boton Enviar a SUNAT, lista de pendientes
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, OUT, SHOTS, STATE] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
const setUrl = (u) => require('child_process').execSync(`psql -h localhost -p 5433 -U postgres env_ui -qc "UPDATE company SET nubecont_api_url='${u}', nubecont_api_token='TKN-SIMULADO-123' WHERE id='${FIKA}'"`);
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const entrar = async (email) => {
    const ctx = await b.newContext({ viewport: { width: 1600, height: 1100 }, timezoneId: 'America/Lima' });
    const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(email + ': ' + e.message));
    p.on('dialog', async d => { R.dialogos = R.dialogos || []; R.dialogos.push(d.message().slice(0, 200)); await d.accept(); });
    await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().endsWith('.css') ? r.fulfill({ body: '', contentType: 'text/css' }) : r.abort());
    await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
    await p.fill('#email', email); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
    await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1200);
    await p.evaluate(async () => { state.view = 'sales'; state.salesTab = 'invoices'; await loadModuleData(); renderView(); }); await p.waitForTimeout(2500);
    return p;
  };
  const notice = (p) => p.evaluate(() => { const n = document.getElementById('globalNotice') || document.querySelector('.notice'); return n ? n.innerText.slice(0, 400) : ''; });
  const filas = (p, docs) => p.evaluate((docs) => docs.map(d => {
    const tr = [...document.querySelectorAll('tr')].find(t => t.innerText.includes(d));
    if (!tr) return [d, 'sin fila'];
    const badge = tr.querySelector('[data-send-badge]');
    return [d, badge ? badge.innerText + (badge.title ? ' | ' + badge.title : '') : '(sin etiqueta)', !!tr.querySelector('[data-action="sale-retry-sunat"]') ? 'boton Enviar' : (!!tr.querySelector('[data-action="sale-consult-sunat"]') ? 'boton Consultar' : '-')];
  }), docs);
  const ventaRapida = async (p, total) => {
    await p.evaluate(() => { state.showSaleForm = true; renderView(); }); await p.waitForTimeout(1200);
    await p.evaluate((total) => {
      const set = (id, v) => { const el = document.getElementById(id); if (el) { el.value = v; el.dispatchEvent(new Event('change', { bubbles: true })); } };
      const inv = document.getElementById('s-use-inventory'); if (inv && inv.checked) { inv.checked = false; inv.dispatchEvent(new Event('change', { bubbles: true })); }
      set('s-customer', 'cli-1'); set('s-doc-type', '01');
      const ser = document.getElementById('s-series'); if (ser) { if (ser.tagName === 'SELECT' && ![...ser.options].some(o => o.value === 'F020')) { const o = document.createElement('option'); o.value = 'F020'; o.text = 'F020'; ser.appendChild(o); } ser.value = 'F020'; }
      set('s-date', '2026-10-22'); set('s-due-date', '2026-10-22');
      set('s-desc', 'SERVICIO PRUEBA PANTALLA'); set('s-qty', '1'); set('s-price', String(total));
    }, total);
    await p.evaluate(() => createQuickSale()); await p.waitForTimeout(9000);
  };
  // 1) Venta desde la pantalla con NubeFact caido
  setUrl('http://127.0.0.1:8949/api/ruta-secreta-xyz');
  const g0 = await entrar('gerente.fika@t.pe');
  R.filas_al_entrar_gerente = await filas(g0, ['F001-000003', 'F030-000119', 'F030-000120']);
  await g0.evaluate(() => { const tr = [...document.querySelectorAll('tr')].find(t => t.innerText.includes('F030-000119')); if (tr) tr.scrollIntoView({ block: 'center' }); });
  await g0.screenshot({ path: `${SHOTS}/1_facturacion_no_enviados.png` });
  const v = await entrar('vendedor.fika@t.pe');
  await ventaRapida(v, 4250);
  R.venta_sin_red_mensaje = await notice(v);
  await v.screenshot({ path: `${SHOTS}/2_quedo_registrada_no_enviada.png` });
  R.venta_sin_red_numero = await v.evaluate(() => (state.cache.sales || []).filter(s => s.series === 'F020').map(s => [s.document_number, s.sunat_status || '', !!s.sunat_ticket]));
  // 2) La tienda intenta emitir la misma venta otra vez: se le ofrece enviar la pendiente (Aceptar)
  setUrl('http://127.0.0.1:8941/api/ruta-secreta-xyz');
  fs.writeFileSync(`${STATE}/escenario.json`, JSON.stringify({ _default: 'ok' }));
  R.dialogos = [];
  await ventaRapida(v, 4250);
  R.repetida_dialogos = R.dialogos; R.repetida_mensaje = await notice(v);
  R.repetida_ventas_F020 = await v.evaluate(() => (state.cache.sales || []).filter(s => s.series === 'F020').map(s => [s.document_number, s.sunat_status || '', !!s.sunat_ticket, s.accounting_status]));
  await v.screenshot({ path: `${SHOTS}/3_repetida_se_envio_la_pendiente.png` });
  // 3) Boton "Enviar a SUNAT" en la fila (F030-000119), con el gerente
  await g0.evaluate(async () => { await loadModuleData(); renderView(); }); await g0.waitForTimeout(2000);
  const btn = g0.locator('tr', { hasText: 'F030-000119' }).locator('[data-action="sale-retry-sunat"]');
  R.boton_existe = await btn.count();
  if (R.boton_existe) { await btn.first().click(); await g0.waitForTimeout(7000); }
  R.boton_mensaje = await notice(g0);
  R.filas_despues = await filas(g0, ['F001-000003', 'F030-000119']);
  await g0.evaluate(() => { const tr = [...document.querySelectorAll('tr')].find(t => t.innerText.includes('F030-000119')); if (tr) tr.scrollIntoView({ block: 'center' }); });
  await g0.screenshot({ path: `${SHOTS}/4_enviado_desde_la_fila.png` });
  R.vendedor_ve_boton_pendientes = await v.evaluate(() => !!document.getElementById('send-pending-btn'));
  // 4) Lista de pendientes (Gerente)
  const g = await entrar('gerente.fika@t.pe');
  await g.waitForTimeout(2000);
  R.gerente_contador = await g.evaluate(() => (document.getElementById('send-pending-count') || {}).innerText || null);
  await g.click('#send-pending-btn'); await g.waitForTimeout(2000);
  R.lista = await g.evaluate(() => [...document.querySelectorAll('#send-pending-overlay tbody tr')].map(t => t.innerText.replace(/\s+/g, ' ').slice(0, 160)));
  await g.screenshot({ path: `${SHOTS}/5_lista_pendientes_gerente.png` });
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1));
  await b.close();
})();
