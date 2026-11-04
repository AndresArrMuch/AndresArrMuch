const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, OUT, SHOTS, PID1] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1000 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().endsWith('.css') ? r.fulfill({ body: '', contentType: 'text/css' }) : r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
  await p.fill('#email', 'tesoreria@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1200);
  await p.evaluate(() => { [...document.querySelectorAll('button[data-view="banks"]')].find(x => x.innerText.includes('Cobranza')).click(); }); await p.waitForTimeout(2500);
  await p.click('[data-bank-tab="transacciones"]'); await p.waitForTimeout(2500);
  // 1) Cobrar seleccionados: F030-000119 (540) + F001-000006 (1018) con el deposito 777001 (900, ya aplicado 790)
  for (const d of ['F001-000006', 'FD01-000001']) await p.locator('tr.cxc-row', { hasText: d }).first().locator('.cxc-select-checkbox').check();
  await p.click('#cxc-multi-collect'); await p.waitForTimeout(800);
  const acc = await p.evaluate(() => (state.cache.bank_accounts || []).find(a => a.account_number === '191-1111111-0-11').id);
  await p.selectOption('#mp-account', acc); await p.fill('#mp-date', '2026-10-18'); await p.fill('#mp-reference', '777003'); await p.waitForTimeout(1800);
  R.multi_info = await p.evaluate(() => (document.getElementById('mp-deposit-info') || {}).innerText || null);
  R.multi_guardar_deshabilitado = await p.evaluate(() => document.getElementById('mp-save-btn').disabled);
  await p.screenshot({ path: `${SHOTS}/1_cobro_varias_pasa_el_deposito.png` });
  // ajustar montos para que quepan (110 disponibles)
  const inputs = p.locator('.mp-item-amount');
  if (await inputs.count() === 2) { await inputs.nth(0).fill('500'); await inputs.nth(1).fill('59'); await p.waitForTimeout(500); }
  R.multi_info_ajustado = await p.evaluate(() => (document.getElementById('mp-deposit-info') || {}).innerText || null);
  R.multi_guardar_deshabilitado_ajustado = await p.evaluate(() => document.getElementById('mp-save-btn').disabled);
  await p.screenshot({ path: `${SHOTS}/2_cobro_ajustado_cabe.png` });
  await p.evaluate(() => document.getElementById('mp-modal').remove());
  // 2) Conciliacion: facturas del deposito 777001 antes y despues de quitar una factura del cobro
  await p.click('[data-bank-tab="conciliacion"]'); await p.waitForTimeout(1500);
  await p.evaluate((acc) => { state._concAccount = acc; state._concMonth = '2026-10'; renderView(); }, acc); await p.waitForTimeout(4000);
  const facturasFila = () => p.evaluate(() => { const tr = [...document.querySelectorAll('tr.conc-tabla-row')].find(t => t.dataset.op === '777001'); return tr ? tr.children[5].innerText : 'sin fila'; });
  R.conc_antes = await facturasFila();
  await p.screenshot({ path: `${SHOTS}/3_conciliacion_antes.png` });
  R.quitar = await p.evaluate(async (pid1) => {
    const doc = (state.cache.sales || []).find(s => s.document_number === 'F001-000003');
    const r = await api('/api/payments/' + state.companyId + '/' + pid1, { method: 'PUT', body: JSON.stringify({ items: [{ document_type: 'sale', document_id: doc.id, amount_applied: 200 }] }) });
    return r?.message || 'ok';
  }, PID1);
  await p.evaluate(() => renderView()); await p.waitForTimeout(4000);
  R.conc_despues = await facturasFila();
  await p.screenshot({ path: `${SHOTS}/4_conciliacion_despues_de_quitar.png` });
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); await b.close();
})();
