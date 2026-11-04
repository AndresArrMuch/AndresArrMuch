const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const [PORT, OUT, SHOT] = process.argv.slice(2);
const FIKA = '976b2dc9-1a6c-4c6f-ba0e-a32b59ceb433';
(async () => {
  const b = await chromium.launch(); const R = { errores_js: [] };
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 }, timezoneId: 'America/Lima' });
  const p = await ctx.newPage(); p.on('pageerror', e => R.errores_js.push(e.message));
  await p.route(/cdnjs\.cloudflare\.com/, r => r.request().url().endsWith('.css') ? r.fulfill({ body: '', contentType: 'text/css' }) : r.abort());
  await p.goto(`http://127.0.0.1:${PORT}/erp`); await p.waitForTimeout(800);
  await p.fill('#email', 'gerente.fika@t.pe'); await p.fill('#password', 'p'); await p.selectOption('#login-company', FIKA).catch(() => {});
  await p.evaluate(() => doLogin()); await p.waitForFunction(() => state.token && !state.loading, null, { timeout: 120000 }); await p.waitForTimeout(1200);
  await p.evaluate(() => { const b = [...document.querySelectorAll('button[data-view="banks"]')].find(x => x.innerText.includes('Cobranza')); b.click(); }); await p.waitForTimeout(3000);
  await p.click('[data-bank-tab="transacciones"]'); await p.waitForTimeout(3000);
  for (const d of ['F030-000120', 'F001-000006', 'F001-000001']) {
    const row = p.locator('tr.cxc-row', { hasText: d });
    if (!(await row.count())) { R[d] = 'sin fila'; continue; }
    R[d] = { fila: (await row.first().innerText()).replace(/\s+/g, ' ') };
    await row.first().click(); await p.waitForTimeout(1500);
    const id = await row.first().getAttribute('data-doc-id');
    R[d].detalle = (await p.locator(`.cxc-detail-row[data-detail-for="${id}"]`).innerText()).replace(/\s+/g, ' ');
  }
  const tr = p.locator('tr.cxc-row', { hasText: 'F030-000120' }).first();
  await tr.scrollIntoViewIfNeeded(); await p.evaluate(() => window.scrollBy(0, -120));
  await p.screenshot({ path: SHOT });
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1)); await b.close();
})();
