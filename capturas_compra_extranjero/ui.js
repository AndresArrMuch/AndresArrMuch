const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, OUT, SHOT] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1000 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().endsWith('.css') ? r.fulfill({ body: '', contentType: 'text/css' }) : r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
  await p.fill('#email', 'gerente.fika@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1200);
  await p.click('button[data-view="purchases"]'); await p.waitForTimeout(2000);
  await p.evaluate(() => { state.purchaseTab = 'foreign'; renderView(); }); await p.waitForTimeout(2000);
  const toast = () => p.evaluate(() => [...document.querySelectorAll('[id*="toast"], .notice')].map(x => x.innerText).filter(Boolean).join(' | ').slice(0, 400));
  const fill = async (supplierText) => {
    await p.evaluate(() => { const h = document.getElementById('pf-supplier'); if (h) h.value = ''; });
    const inp = p.locator('#pf-supplier-ac input'); await inp.fill(supplierText); await p.keyboard.press('Escape');
    await p.fill('#pf-series', 'INV'); await p.fill('#pf-corr', 'A260708958H');
    await p.fill('#pf-date', '2026-09-09'); await p.evaluate(() => document.getElementById('pf-date').dispatchEvent(new Event('change')));
    await p.fill('#pf-due-date', '2026-09-09');
    await p.selectOption('#pf-country', { index: 1 }).catch(() => {});
    await p.selectOption('#pf-currency', 'USD').catch(() => {}); await p.waitForTimeout(300); await p.fill('#pf-exchange-rate', '3.36');
    await p.fill('#pf-taxed-amount', '0').catch(() => {});
    await p.fill('#pf-desc', 'DAM 118-2026-10-515757 -01-6-00'); await p.fill('#pf-qty', '1');
    const cb = p.locator('#pf-has-untaxed-costs'); if (!(await cb.isChecked())) await cb.check();
    await p.fill('#pf-untaxed-amount', '70840');
  };
  // 1) Proveedor que NO existe con ese nombre
  await fill('BLUE SAIL HK');
  await p.evaluate(() => createForeignPurchase()); await p.waitForTimeout(2500);
  R.no_existe = await toast();
  // 2) Nombre exacto escrito a mano (como en la captura)
  await fill('BLUE SAIL (HONG KONG) TRADING LIMITED');
  await p.evaluate(() => createForeignPurchase()); await p.waitForTimeout(4000);
  R.nombre_exacto = await toast();
  R.compras = await p.evaluate(async () => ((await api('/api/purchases/' + state.companyId + '?page=1&per_page=200')).data?.data || []).filter(x => x.correlative === 'A260708958H').map(x => ({ numero: x.document_number, subtotal: x.subtotal, igv: x.igv, total: x.total, moneda: x.currency, tc: x.exchange_rate })));
  await p.screenshot({ path: SHOT });
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); await b.close();
})();
