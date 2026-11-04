const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, OUT, SHOT] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [], dialogos: [] };
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1000 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  p.on('dialog', async d => { R.dialogos.push(d.message().slice(0, 400)); await d.accept(); });
  await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().endsWith('.css') ? r.fulfill({ body: '', contentType: 'text/css' }) : r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
  await p.fill('#email', 'tesoreria@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1200);
  await p.evaluate(() => { [...document.querySelectorAll('button[data-view="banks"]')].find(x => x.innerText.includes('Cobranza')).click(); }); await p.waitForTimeout(2500);
  await p.click('[data-bank-tab="transacciones"]'); await p.waitForTimeout(2500);
  const row = p.locator('tr.cxc-row', { hasText: 'F001-000005' }).first();
  await row.click(); await p.waitForTimeout(1500);
  const id = await row.getAttribute('data-doc-id');
  const det = p.locator(`.cxc-detail-row[data-detail-for="${id}"]`);
  R.detalle_antes = (await det.innerText()).replace(/\s+/g, ' ');
  R.boton_quitar = await det.locator('.btn-remove-doc-payment').count();
  await det.scrollIntoViewIfNeeded(); await p.screenshot({ path: SHOT.replace('.png', '_antes.png') });
  if (R.boton_quitar) { await det.locator('.btn-remove-doc-payment').first().click(); await p.waitForTimeout(3500); }
  R.aviso = await p.evaluate(() => (document.querySelector('.notice') || {}).innerText || '');
  R.filas = await p.evaluate(() => ['F001-000003', 'F001-000005', 'B001-000001'].map(d => { const tr = [...document.querySelectorAll('tr.cxc-row')].find(t => t.innerText.includes(d)); return tr ? tr.innerText.replace(/\s+/g, ' ').slice(0, 140) : d + ' sin fila'; }));
  await p.screenshot({ path: SHOT });
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); await b.close();
})();
